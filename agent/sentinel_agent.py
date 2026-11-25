import os, socket, ipaddress, json, urllib.request, platform, subprocess, time, argparse

API_URL = os.getenv("SENTINEL_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "change-me-in-production")
SUBNET = os.getenv("AUTHORIZED_SUBNET", "192.168.1.0/24")
AGENT_VERSION = "1.0.0"

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    r = subprocess.run(["ping", param, "1", "-w", "1000", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0

def arp_table():
    table = {}
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=30)
        for line in out.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and "-" in parts[1]:
                ip = parts[0]
                mac = parts[1].replace("-", ":").upper()
                table[ip] = mac
    except Exception:
        pass
    return table

OUI_DB = {
    "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",
    "DC:A6:32": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
}

def vendor_from_mac(mac):
    if not mac or mac == "No disponible":
        return "Desconocido"
    return OUI_DB.get(mac[:8].upper(), "Desconocido")

def discover(subnet):
    net = ipaddress.ip_network(subnet, strict=False)
    table = {}
    devices = []
    for host in net.hosts():
        ip = str(host)
        if not ping(ip):
            continue
        # refresh ARP after ping
        if not table:
            table = arp_table()
        mac = table.get(ip, "No disponible")
        hostname = "No disponible"
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = "No disponible"
        vendor = vendor_from_mac(mac)
        dev_type = "computador" if hostname != "No disponible" else "desconocido"
        devices.append({"ip": ip, "mac": mac, "vendor": vendor,
                        "hostname": hostname, "device_type": dev_type,
                        "status": "active", "source": "agent"})
    # refresh table once more for MACs
    table = arp_table()
    for d in devices:
        if d["mac"] == "No disponible":
            d["mac"] = table.get(d["ip"], "No disponible")
            d["vendor"] = vendor_from_mac(d["mac"])
    return devices

def collect_software():
    if platform.system().lower() != "windows":
        return []
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object { $_.DisplayName } | Select-Object DisplayName, DisplayVersion | ConvertTo-Json -Compress"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if not out.stdout.strip():
            return []
        parsed = json.loads(out.stdout)
        if isinstance(parsed, dict):
            parsed = [parsed]
        return [{"name": p.get("DisplayName"), "version": p.get("DisplayVersion")} for p in parsed if p.get("DisplayName")]
    except Exception:
        return []

def local_ip():
    """IP LAN de la máquina donde corre el agente (para asociar el software al dispositivo)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return None

PS_NETWORK_SCRIPT = """
$ErrorActionPreference = 'SilentlyContinue'
$out = @()
foreach ($cfg in (Get-NetIPConfiguration)) {
  $mac = $null; $type = $null; $st = $null
  if ($cfg.NetAdapter) {
    $mac = $cfg.NetAdapter.MacAddress
    $type = $cfg.NetAdapter.InterfaceDescription
    $st = $cfg.NetAdapter.Status
  }
  $gw = (@($cfg.IPv4DefaultGateway) | ForEach-Object { $_.NextHop }) -join ','
  $dns = (@($cfg.DNSServer) | Where-Object { $_.AddressFamily -eq 2 } | ForEach-Object { $_.ServerAddresses }) -join ','
  foreach ($a in @($cfg.IPv4Address)) {
    if (-not $a) { continue }
    $out += [PSCustomObject]@{
      interface      = [string]$cfg.InterfaceAlias
      type           = [string]$type
      status         = [string]$st
      mac            = [string]$mac
      ip             = [string]$a.IPAddress
      prefix_length  = [int]$a.PrefixLength
      gateway        = [string]$gw
      dns            = [string]$dns
    }
  }
}
ConvertTo-Json -InputObject @($out) -Compress
"""

PS_HOST_SCRIPT = """
$ErrorActionPreference = 'SilentlyContinue'
$os = (Get-CimInstance Win32_OperatingSystem).Caption
[PSCustomObject]@{ name = $env:COMPUTERNAME; os = [string]$os } | ConvertTo-Json -Compress
"""

def _run_ps(script, timeout=60):
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, timeout=timeout)
        return (out.stdout or "").strip()
    except Exception:
        return ""

def collect_network():
    """Interfaces IPv4 reales de la máquina donde corre el agente (Windows).

    Devuelve (interfaces, nombre_equipo, sistema_operativo).
    Solo se recolecta información real del equipo local: para el resto de hosts
    el agente solo conoce IP/MAC (ARP) y nombre por DNS inverso.
    """
    if platform.system().lower() != "windows":
        return [], None, None
    interfaces = []
    txt = _run_ps(PS_NETWORK_SCRIPT)
    if txt and txt not in ("null", "[]"):
        try:
            parsed = json.loads(txt)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for p in parsed:
                if not isinstance(p, dict) or not p.get("ip"):
                    continue
                interfaces.append({
                    "ip": str(p.get("ip")).strip(),
                    "mac": (p.get("mac") or "").strip().replace("-", ":").upper() or None,
                    "interface_name": (p.get("interface") or "").strip() or None,
                    "interface_type": (p.get("type") or "").strip() or None,
                    "status": (p.get("status") or "").strip() or None,
                    "prefix_length": int(p.get("prefix_length")) if str(p.get("prefix_length") or "").isdigit() else None,
                    "gateway": (p.get("gateway") or "").strip() or None,
                    "dns": (p.get("dns") or "").strip() or None,
                })
        except Exception:
            interfaces = []
    host_txt = _run_ps(PS_HOST_SCRIPT)
    name, os_name = None, None
    if host_txt and host_txt not in ("null",):
        try:
            h = json.loads(host_txt)
            if isinstance(h, dict):
                name = (h.get("name") or "").strip() or None
                os_name = (h.get("os") or "").strip() or None
        except Exception:
            pass
    if not name:
        name = platform.node() or None
    if not os_name:
        os_name = f"{platform.system()} {platform.release()}"
    return interfaces, name, os_name

def upload(devices, software=None, host_ip=None, agent_host=None):
    payload = {"devices": devices}
    if software:
        payload["software"] = software
        if host_ip:
            payload["software_host_ip"] = host_ip
    if agent_host:
        payload["agent_host"] = agent_host
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{API_URL}/api/discovery/agent", data=data, headers={
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

POLL_INTERVAL = int(os.getenv("AGENT_POLL_INTERVAL", "5"))

def claim_request():
    req = urllib.request.Request(f"{API_URL}/api/discovery/requests/claim", data=b"{}", headers={
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def complete_request(request_id, status, discovered_count=0, rejected_count=0, error_message=None, received_count=None, confirmed_count=None, updated_count=None, archived_count=None):
    payload = {"status": status, "discovered_count": discovered_count, "rejected_count": rejected_count}
    if received_count is not None:
        payload["received_count"] = received_count
    if confirmed_count is not None:
        payload["confirmed_count"] = confirmed_count
    if updated_count is not None:
        payload["updated_count"] = updated_count
    if archived_count is not None:
        payload["archived_count"] = archived_count
    if error_message:
        payload["error_message"] = error_message
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{API_URL}/api/discovery/requests/{request_id}/complete", data=data, headers={
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def heartbeat():
    try:
        payload = {"version": AGENT_VERSION, "status": "online"}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{API_URL}/api/agent/heartbeat", data=data, headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }, method="POST")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Heartbeat fallido: {e}")
        return None

def run_once(subnet):
    devs = discover(subnet)
    print(f"Descubiertos: {len(devs)}")
    sw = collect_software()
    print(f"Software detectado: {len(sw)}")
    net_ifaces, host_name, host_os = collect_network()
    print(f"Interfaces de red del agente: {len(net_ifaces)}")
    local_ips = {i["ip"] for i in net_ifaces}
    agent_host = None
    target = next((d for d in devs if d["ip"] in local_ips), None)
    if target is not None:
        target["network"] = net_ifaces
        target["name"] = host_name
        target["os_info"] = host_os
    elif net_ifaces:
        # el equipo del agente no está entre los descubiertos: se envía aparte
        agent_host = {"ip": local_ip() or net_ifaces[0]["ip"], "name": host_name,
                      "os": host_os, "network": net_ifaces}
    host_ip = local_ip()
    result = upload(devs, sw, host_ip, agent_host)
    print(result)
    return devs, sw, result

def run_daemon():
    print("Agente SentinelAI en modo daemon. Ctrl+C para detener.")
    while True:
        try:
            heartbeat()
            claim = claim_request()
            rid = claim.get("id")
            if not rid:
                time.sleep(POLL_INTERVAL)
                continue
            subnet = claim.get("subnet") or SUBNET
            print(f"Solicitud reclamada: {rid} ({subnet})")
            try:
                devs, sw, result = run_once(subnet)
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        complete_request(rid, "completed",
                                         discovered_count=len(devs),
                                         rejected_count=result.get("rechazados", 0),
                                         received_count=result.get("recibidos", len(devs)),
                                         confirmed_count=result.get("confirmed_count", 0),
                                         updated_count=result.get("updated_count", 0),
                                         archived_count=result.get("archived_count", 0))
                        print(f"Solicitud {rid} completada")
                        break
                    except Exception as e:
                        print(f"Error completando solicitud {rid}: {e}")
                        if attempt < max_retries:
                            time.sleep(5 * attempt)
                        else:
                            raise
            except Exception as e:
                print(f"Error en descubrimiento: {e}")
                try:
                    complete_request(rid, "error", 0, 0, str(e))
                except Exception as e2:
                    print(f"No se pudo reportar error: {e2}")
        except Exception as e:
            print(f"Error de comunicación con backend: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    if args.daemon or os.getenv("AGENT_DAEMON", "").lower() in ("1", "true", "yes"):
        run_daemon()
    else:
        try:
            run_once(SUBNET)
        except Exception as e:
            print(f"Error al enviar: {e}")