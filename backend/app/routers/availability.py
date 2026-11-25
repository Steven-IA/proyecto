from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.device_service import set_status
from ..services.event_service import log_event
from ..discovery.discovery import ping_host

router = APIRouter(prefix="/api/availability", tags=["availability"])

@router.post("/check/{device_id}")
def check_device(device_id: int, db: Session = Depends(get_db)):
    from ..models.models import Device
    dev = db.query(Device).filter(Device.id == device_id).first()
    if not dev:
        return {"error": "Dispositivo no encontrado"}
    status = "active" if ping_host(dev.ip) else "inactive"
    set_status(db, device_id, status)
    log_event(db, "availability", f"Dispositivo {device_id} está {status}", device_id)
    return {"device_id": device_id, "status": status}