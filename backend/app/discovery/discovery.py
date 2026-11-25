import ipaddress
import socket
import subprocess
import platform
from typing import List, Dict

def is_authorized(ip: str, subnet: str) -> bool:
    try:
        net = ipaddress.ip_network(subnet, strict=False)
        return ipaddress.ip_address(ip) in net
    except ValueError:
        return False

def ping_host(ip: str) -> bool:
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(["ping", param, "1", "-w", "1000", ip],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

OUI_DB = {
    "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",
    "dc:a6:32": "Raspberry Pi",
    "b8:27:eb": "Raspberry Pi",
}

def vendor_from_mac(mac: str) -> str:
    if not mac:
        return "Desconocido"
    prefix = mac.upper()[:8]
    return OUI_DB.get(prefix, "Desconocido")

def classify_device(hostname: str, vendor: str, open_ports: List[int]) -> str:
    h = (hostname or "").lower()
    v = (vendor or "").lower()
    if "printer" in h or 9100 in open_ports or 631 in open_ports:
        return "impresora"
    if "raspberry" in v:
        return "servidor"
    if any(p in open_ports for p in (80, 443, 22)):
        return "servidor"
    if hostname and hostname != "No disponible":
        return "computador"
    return "desconocido"

def try_arp_mac(ip: str) -> str:
    # Optional ARP lookup (may require privileges/network access)
    try:
        import scapy.all as scapy  # type: ignore
        ans = scapy.arping(ip, timeout=1, verbose=False)
        for _, rcv in ans[0]:
            return rcv.hwsrc
    except Exception:
        return ""
    return ""

def discover_subnet(subnet: str) -> List[Dict]:
    net = ipaddress.ip_network(subnet, strict=False)
    results = []
    for host in net.hosts():
        ip = str(host)
        if not is_authorized(ip, subnet):
            continue
        alive = ping_host(ip)
        mac = try_arp_mac(ip) if alive else ""
        # If ICMP fails but ARP evidence exists, consider confirmed
        if not alive and mac:
            alive = True
        if not alive:
            continue
        hostname = "No disponible"
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = "No disponible"
        vendor = vendor_from_mac(mac)
        dev_type = classify_device(hostname, vendor, [])
        results.append({
            "ip": ip,
            "mac": mac or "No disponible",
            "vendor": vendor,
            "hostname": hostname,
            "device_type": dev_type,
            "status": "active",
            "source": "discovered"
        })
    return results