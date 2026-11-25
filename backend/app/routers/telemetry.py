from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..config import settings
from ..security.auth import require_api_key
from ..models.models import NetworkTelemetry, Device
from ..schemas.schemas import TelemetryIn
import math, os, ipaddress, time

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

_RATE_LIMIT = {}
_RATE_LIMIT_MAX = int(os.getenv("TELEMETRY_RATE_LIMIT_PER_MINUTE", "60"))
_RATE_LIMIT_WINDOW = 60

def _check_rate_limit(key: str):
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    entries = [t for t in _RATE_LIMIT.get(key, []) if t > window_start]
    if len(entries) >= _RATE_LIMIT_MAX:
        return False
    entries.append(now)
    _RATE_LIMIT[key] = entries
    return True

def _valid_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return False
    return True

def _validate_timestamp(ts: datetime):
    now = datetime.utcnow()
    if ts.tzinfo is not None:
        ts = ts.replace(tzinfo=None)
    if abs((now - ts).total_seconds()) > 300:
        return False
    return True

@router.post("")
def ingest_telemetry(payload: TelemetryIn, request: Request, db: Session = Depends(get_db), _=Depends(require_api_key)):
    if not payload.is_complete:
        raise HTTPException(status_code=400, detail="Muestra incompleta")
    for field in ("conn_count","conn_freq","ports","bytes_sent","bytes_recv","duration","activity_var","comm_freq"):
        if not _valid_number(getattr(payload, field)):
            raise HTTPException(status_code=400, detail=f"Valor inválido en {field}")
    if not _validate_timestamp(payload.timestamp):
        raise HTTPException(status_code=400, detail="Timestamp fuera de tolerancia")
    # rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Límite de solicitudes excedido")

    # IP validation
    local_ip = None
    if payload.local_ip:
        try:
            local_ip = str(ipaddress.ip_address(payload.local_ip))
        except ValueError:
            raise HTTPException(status_code=400, detail="IP local inválida")

    # device association
    device_id = payload.device_id
    if device_id is not None:
        dev = db.query(Device).filter(Device.id == device_id, Device.confirmed == True).first()
        if not dev:
            raise HTTPException(status_code=400, detail="Dispositivo no encontrado o no confirmado")
    else:
        if local_ip:
            dev = db.query(Device).filter(Device.ip == local_ip, Device.confirmed == True).first()
            device_id = dev.id if dev else None

    identity_key = f"device:{device_id}" if device_id is not None else f"ip:{local_ip or 'unknown'}"

    # duplicate check
    existing = db.query(NetworkTelemetry).filter(
        NetworkTelemetry.identity_key == identity_key,
        NetworkTelemetry.timestamp == payload.timestamp,
        NetworkTelemetry.window_seconds == payload.window_seconds,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Muestra duplicada")

    row = NetworkTelemetry(
        device_id=device_id,
        identity_key=identity_key,
        source="agent",
        local_ip=local_ip,
        timestamp=payload.timestamp,
        conn_count=payload.conn_count,
        conn_freq=payload.conn_freq,
        ports=payload.ports,
        bytes_sent=payload.bytes_sent,
        bytes_recv=payload.bytes_recv,
        duration=payload.duration,
        activity_var=payload.activity_var,
        comm_freq=payload.comm_freq,
        window_seconds=payload.window_seconds,
        is_complete=payload.is_complete,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # retention
    days = int(os.getenv("TELEMETRY_RETENTION_DAYS", "30"))
    cutoff = datetime.utcnow() - timedelta(days=days)
    db.query(NetworkTelemetry).filter(NetworkTelemetry.created_at < cutoff).delete()
    db.commit()
    return {"id": row.id, "device_id": row.device_id, "status": "almacenada"}

@router.get("")
def list_telemetry(device_id: int = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(NetworkTelemetry)
    if device_id:
        q = q.filter(NetworkTelemetry.device_id == device_id)
    rows = q.order_by(NetworkTelemetry.timestamp.desc()).limit(limit).all()
    return [{"id": r.id, "device_id": r.device_id, "timestamp": r.timestamp, "conn_count": r.conn_count, "conn_freq": r.conn_freq, "ports": r.ports, "bytes_sent": r.bytes_sent, "bytes_recv": r.bytes_recv, "duration": r.duration, "activity_var": r.activity_var, "comm_freq": r.comm_freq, "is_complete": r.is_complete} for r in rows]