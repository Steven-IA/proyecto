import ipaddress
from sqlalchemy.orm import Session
from ..models.models import AppSetting

DEFAULTS = {
    "authorized_subnet": "192.168.1.0/24",
    "discovery_interval_minutes": "60",
    "agent_enabled": "true",
}

def get_setting(db: Session, key: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        return row.value
    return DEFAULTS.get(key, "")

def set_setting(db: Session, key: str, value: str):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()

def get_all(db: Session):
    return {k: get_setting(db, k) for k in DEFAULTS}

def validate(key: str, value: str):
    if key == "authorized_subnet":
        ipaddress.ip_network(value, strict=False)
    elif key == "discovery_interval_minutes":
        v = int(value)
        if v < 1 or v > 1440:
            raise ValueError("Intervalo fuera de rango")
    elif key == "agent_enabled":
        if value not in ("true", "false"):
            raise ValueError("Valor inválido")