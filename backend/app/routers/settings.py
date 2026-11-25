from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.settings_service import get_all, set_setting, validate

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
def read_settings(db: Session = Depends(get_db)):
    return get_all(db)

@router.put("/{key}")
def update_setting(key: str, payload: dict, db: Session = Depends(get_db)):
    if key not in ("authorized_subnet", "discovery_interval_minutes", "agent_enabled"):
        raise HTTPException(status_code=400, detail="Parámetro no permitido")
    value = str(payload.get("value", ""))
    try:
        validate(key, value)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    set_setting(db, key, value)
    return {"key": key, "value": value, "mensaje": "Configuración actualizada"}