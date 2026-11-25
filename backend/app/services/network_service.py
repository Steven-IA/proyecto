from sqlalchemy.orm import Session
from datetime import datetime
import ipaddress
from ..models.models import NetworkInterface

UNKNOWN_VALUES = (None, "", "No disponible", "Desconocido")


def _set_if_valid(row, field, value):
    """No sobrescribe un valor válido con una colección incompleta/vacía."""
    if value in UNKNOWN_VALUES:
        return False
    if isinstance(value, int) and value <= 0:
        return False
    setattr(row, field, value)
    return True


def _derive_network(ip: str, prefix, netmask=None):
    """Subred y máscara derivadas de la IP + prefijo (nunca inventadas)."""
    try:
        if prefix:
            net = ipaddress.ip_network(f"{ip}/{int(prefix)}", strict=False)
            return str(net), str(net.netmask)
        if netmask:
            net = ipaddress.ip_network(f"{ip}/{netmask}", strict=False)
            return str(net), str(net.netmask)
    except Exception:
        pass
    return None, None


def sync_interfaces(db: Session, device, interfaces, source: str = "agent") -> dict:
    """Sincroniza las interfaces de red de un dispositivo.

    Reglas:
    - Colección vacía o inválida -> no se toca nada (no se borran datos válidos).
    - Sin duplicados: upsert por (device_id, ip).
    - Solo se sobrescriben campos con valor real (no vacíos ni "No disponible").
    - Las interfaces que desaparecen de una colección completa se marcan inactivas,
      nunca se eliminan (se conserva el histórico).
    - Se marca como principal la interfaz con la IP del dispositivo.
    """
    result = {"recibidas": 0, "creadas": 0, "actualizadas": 0, "inactivas": 0, "omitidas": 0, "mac_dispositivo": False}
    if not device or not isinstance(interfaces, list):
        return result
    valid = [i for i in interfaces if isinstance(i, dict) and i.get("ip")]
    if not valid:
        # recolección incompleta: no modifica lo ya persistido
        return result

    now = datetime.utcnow()
    touched = []
    for itf in valid:
        ip = str(itf["ip"]).strip()
        if not ip:
            continue
        result["recibidas"] += 1
        prefix = itf.get("prefix_length") or itf.get("prefix")
        netmask = itf.get("netmask")
        subnet, derived_mask = _derive_network(ip, prefix, netmask)
        row = (
            db.query(NetworkInterface)
            .filter(NetworkInterface.device_id == device.id, NetworkInterface.ip == ip)
            .first()
        )
        if row is None:
            row = NetworkInterface(device_id=device.id, ip=ip, source=source,
                                   first_seen=now, last_seen=now)
            db.add(row)
            result["creadas"] += 1
        else:
            result["actualizadas"] += 1

        _set_if_valid(row, "mac", itf.get("mac"))
        _set_if_valid(row, "gateway", itf.get("gateway"))
        _set_if_valid(row, "dns", itf.get("dns"))
        _set_if_valid(row, "interface_name", itf.get("interface_name") or itf.get("interface"))
        _set_if_valid(row, "interface_type", itf.get("interface_type") or itf.get("type"))
        prefix_val = None
        try:
            if prefix not in (None, ""):
                prefix_val = int(prefix)
        except (TypeError, ValueError):
            prefix_val = None
        _set_if_valid(row, "prefix_length", prefix_val)
        _set_if_valid(row, "netmask", netmask or derived_mask)
        _set_if_valid(row, "subnet", itf.get("subnet") or subnet)
        status = (itf.get("status") or "").strip().lower()
        if status:
            row.status = "up" if status in ("up", "active", "connected") else status
        row.last_seen = now
        touched.append(row)

    # autoflush está deshabilitado: flush explícito para ver las filas nuevas
    db.flush()
    rows = db.query(NetworkInterface).filter(NetworkInterface.device_id == device.id).all()
    target = next((r for r in rows if r.ip == device.ip), None)
    if target is None and touched:
        target = touched[0]
    for row in rows:
        row.is_primary = (row is target)
        if not any(row is t for t in touched) and row.status != "inactive":
            row.status = "inactive"
            result["inactivas"] += 1

    # Si el dispositivo no tiene MAC conocida, usa la de su interfaz principal
    # (dato real del adaptador, no inventado).
    if target is not None and target.mac:
        current = (device.mac or "").strip()
        if current in ("", "No disponible", "Desconocido"):
            device.mac = target.mac
            result["mac_dispositivo"] = True

    db.commit()
    return result


def list_interfaces(db: Session, device_id: int):
    return (
        db.query(NetworkInterface)
        .filter(NetworkInterface.device_id == device_id)
        .order_by(NetworkInterface.is_primary.desc(), NetworkInterface.ip)
        .all()
    )


def primary_interface(db: Session, device_id: int):
    return (
        db.query(NetworkInterface)
        .filter(NetworkInterface.device_id == device_id, NetworkInterface.is_primary == True)
        .first()
    )
