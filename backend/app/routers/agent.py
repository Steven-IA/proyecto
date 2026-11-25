from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..security.auth import require_api_key
from ..services.settings_service import get_setting, set_setting

router = APIRouter(prefix="/api/agent", tags=["agent"])

@router.post("/heartbeat")
def heartbeat(payload: dict, db: Session = Depends(get_db), _=Depends(require_api_key)):
    version = str(payload.get("version", "unknown"))
    status = str(payload.get("status", "online"))
    set_setting(db, "agent_last_seen", datetime.utcnow().isoformat())
    set_setting(db, "agent_version", version)
    set_setting(db, "agent_status", status)
    return {"ok": True}

@router.get("/status")
def agent_status(db: Session = Depends(get_db)):
    last_seen = get_setting(db, "agent_last_seen")
    version = get_setting(db, "agent_version")
    status = get_setting(db, "agent_status")
    connected = False
    if last_seen:
        try:
            dt = datetime.fromisoformat(last_seen)
            connected = (datetime.utcnow() - dt).total_seconds() < 30
        except Exception:
            connected = False
    return {
        "connected": connected,
        "last_seen": last_seen,
        "version": version or "desconocida",
        "status": status or "desconocido",
    }