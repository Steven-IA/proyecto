from sqlalchemy.orm import Session
from datetime import datetime
from ..models.models import Device, DeviceHistory

# Valores que indican "sin dato": nunca degradan un valor ya conocido.
UNKNOWN_MARKERS = ("No disponible", "Desconocido", "unknown", "desconocido")

def upsert_device(db: Session, data: dict) -> Device:
    data = dict(data)
    data.pop("network", None)  # las interfaces se persisten aparte
    dev = db.query(Device).filter(Device.ip == data["ip"]).first()
    if dev:
        for k, v in data.items():
            if not hasattr(dev, k):
                continue
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue  # no sobrescribir con cadenas vacías
            current = getattr(dev, k)
            if v in UNKNOWN_MARKERS and current not in (None, "") and current not in UNKNOWN_MARKERS:
                continue  # no degradar un dato válido con "No disponible"
            setattr(dev, k, v)
        dev.last_seen = datetime.utcnow()
    else:
        dev = Device(**data)
        db.add(dev)
    db.commit()
    db.refresh(dev)
    hist = DeviceHistory(device_id=dev.id, status=dev.status, note="Descubrimiento")
    db.add(hist)
    db.commit()
    return dev

def get_devices(db: Session, confirmed_only: bool = True, include_deleted: bool = False):
    q = db.query(Device)
    if confirmed_only:
        q = q.filter(Device.confirmed == True)
    if not include_deleted:
        q = q.filter(Device.deleted_at.is_(None))
    return q.all()

def get_device(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()

def set_status(db: Session, device_id: int, status: str):
    dev = get_device(db, device_id)
    if dev:
        dev.status = status
        dev.last_seen = datetime.utcnow()
        db.add(DeviceHistory(device_id=dev.id, status=status, note="Comprobación de disponibilidad"))
        db.commit()
        db.refresh(dev)
    return dev