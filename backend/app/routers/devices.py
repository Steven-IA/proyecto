from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.device_service import get_devices, get_device
from ..services.software_service import list_device_software
from ..services.network_service import list_interfaces
from ..schemas.schemas import DeviceOut, DeviceDetail, NetworkInterfaceOut, SoftwareOut
from ..services.audit_service import record_deletion
from ..models.models import Device, SoftwareInventory, NetworkInterface, DiscoveryRequest
from datetime import datetime

router = APIRouter(prefix="/api/devices", tags=["devices"])

def _device_payload(dev: Device, interfaces=None) -> dict:
    """Serializa un dispositivo con la información de red realmente persistida."""
    interfaces = interfaces if interfaces is not None else []
    primary = next((i for i in interfaces if i.is_primary), interfaces[0] if interfaces else None)
    return {
        "id": dev.id,
        "ip": dev.ip,
        "mac": dev.mac,
        "vendor": dev.vendor,
        "hostname": dev.hostname,
        "name": dev.name,
        "device_type": dev.device_type,
        "os_info": dev.os_info,
        "status": dev.status,
        "risk_level": dev.risk_level,
        "source": dev.source,
        "confirmed": dev.confirmed,
        "deleted_at": dev.deleted_at,
        "first_seen": dev.first_seen,
        "last_seen": dev.last_seen,
        "subnet": primary.subnet if primary else None,
        "gateway": primary.gateway if primary else None,
        "dns": primary.dns if primary else None,
        "interface_count": len(interfaces),
    }

def _interfaces_by_device(db: Session, device_ids) -> dict:
    if not device_ids:
        return {}
    rows = (
        db.query(NetworkInterface)
        .filter(NetworkInterface.device_id.in_(list(device_ids)))
        .order_by(NetworkInterface.is_primary.desc(), NetworkInterface.ip)
        .all()
    )
    grouped = {}
    for r in rows:
        grouped.setdefault(r.device_id, []).append(r)
    return grouped

@router.get("/", response_model=list[DeviceOut])
def list_devices(confirmed_only: bool = Query(True), include_deleted: bool = Query(False), db: Session = Depends(get_db)):
    devs = get_devices(db, confirmed_only=confirmed_only, include_deleted=include_deleted)
    grouped = _interfaces_by_device(db, [d.id for d in devs])
    return [_device_payload(d, grouped.get(d.id, [])) for d in devs]

@router.get("/summary")
def devices_summary(db: Session = Depends(get_db)):
    """Agregados persistidos del inventario (fuente del Dashboard)."""
    base = db.query(Device).filter(Device.deleted_at.is_(None))
    total = base.count()
    confirmed = base.filter(Device.confirmed == True).count()
    active = base.filter(Device.status == "active").count()
    inactive = base.filter(Device.status == "inactive").count()
    high_risk = base.filter(Device.risk_level == "high").count()
    archived = db.query(Device).filter(Device.deleted_at.is_not(None)).count()
    software_total = db.query(SoftwareInventory).count()
    software_linked = db.query(SoftwareInventory).filter(SoftwareInventory.device_id.is_not(None)).count()
    interfaces_total = db.query(NetworkInterface).count()
    interfaces_active = db.query(NetworkInterface).filter(NetworkInterface.status == "up").count()
    ips_registradas = db.query(NetworkInterface.ip).distinct().count()
    ultimo_descubrimiento = None
    last_req = db.query(DiscoveryRequest).filter(DiscoveryRequest.finished_at.is_not(None)).order_by(DiscoveryRequest.finished_at.desc()).first()
    if last_req:
        ultimo_descubrimiento = last_req.finished_at
    else:
        last_dev = base.order_by(Device.last_seen.desc()).first()
        ultimo_descubrimiento = last_dev.last_seen if last_dev else None
    return {
        "total_dispositivos": total,
        "confirmados": confirmed,
        "activos": active,
        "inactivos": inactive,
        "riesgo_alto": high_risk,
        "archivados": archived,
        "software_total": software_total,
        "software_asociado": software_linked,
        "interfaces_total": interfaces_total,
        "interfaces_activas": interfaces_active,
        "ips_registradas": ips_registradas,
        "ultimo_descubrimiento": ultimo_descubrimiento,
    }

@router.get("/{device_id}/interfaces", response_model=list[NetworkInterfaceOut])
def device_interfaces(device_id: int, db: Session = Depends(get_db)):
    dev = get_device(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return list_interfaces(db, device_id)

@router.get("/{device_id}/software", response_model=list[SoftwareOut])
def device_software(device_id: int, db: Session = Depends(get_db)):
    dev = get_device(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return list_device_software(db, device_id)

@router.post("/{device_id}/restore")
def restore_device(device_id: int, db: Session = Depends(get_db)):
    """Restaura de forma explícita un dispositivo archivado (nunca automático)."""
    dev = db.query(Device).filter(Device.id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if dev.deleted_at is None:
        raise HTTPException(status_code=400, detail="El dispositivo no está archivado")
    dev.deleted_at = None
    dev.confirmed = True
    dev.last_seen = datetime.utcnow()
    record_deletion(db, "device", "restore", count=1, entity_id=device_id, details={"ip": dev.ip})
    db.commit()
    db.refresh(dev)
    return {"restaurados": 1, "mensaje": "Dispositivo restaurado", "device_id": dev.id}

@router.delete("/bulk")
def bulk_delete_devices(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="Lista de IDs inválida")
    unique_ids = list(set(ids))
    devs = db.query(Device).filter(Device.id.in_(unique_ids)).all()
    found_ids = {d.id for d in devs}
    missing = [i for i in unique_ids if i not in found_ids]
    archived = 0
    for dev in devs:
        if dev.deleted_at is None:
            dev.deleted_at = datetime.utcnow()
            archived += 1
    record_deletion(db, "device", "bulk_soft_delete", count=archived, details={"ids": unique_ids, "missing": missing})
    db.commit()
    return {"eliminados": archived, "no_encontrados": len(missing), "mensaje": f"{archived} dispositivos archivados"}

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    dev = db.query(Device).filter(Device.id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if dev.deleted_at is not None:
        raise HTTPException(status_code=400, detail="El dispositivo ya está archivado")
    dev.deleted_at = datetime.utcnow()
    record_deletion(db, "device", "soft_delete", count=1, entity_id=device_id, details={"ip": dev.ip})
    db.commit()
    return {"eliminados": 1, "mensaje": "Dispositivo archivado"}

@router.get("/{device_id}", response_model=DeviceDetail)
def device_detail(device_id: int, db: Session = Depends(get_db)):
    dev = get_device(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    ifaces = list_interfaces(db, device_id)
    payload = _device_payload(dev, ifaces)
    payload["interfaces"] = [
        {
            "id": i.id, "device_id": i.device_id, "ip": i.ip, "mac": i.mac,
            "prefix_length": i.prefix_length, "netmask": i.netmask, "subnet": i.subnet,
            "gateway": i.gateway, "dns": i.dns, "interface_name": i.interface_name,
            "interface_type": i.interface_type, "status": i.status, "is_primary": i.is_primary,
            "source": i.source, "first_seen": i.first_seen, "last_seen": i.last_seen,
        }
        for i in ifaces
    ]
    return payload
