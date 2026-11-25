import os
import time
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.models import EventLog, NetworkTelemetry, Alert, CleanupRun, AppSetting, CleanupLock

def get_setting(db: Session, key: str, default: str = ""):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else default

def is_cleanup_enabled(db: Session) -> bool:
    return get_setting(db, "cleanup_enabled", "false").lower() == "true"

def get_frequency_seconds(db: Session) -> int:
    val = get_setting(db, "cleanup_frequency", "daily")
    if val == "weekly":
        return 604800
    return 86400

def candidate_events(db: Session, retention_days: int):
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    excluded = {"security", "audit", "deletion"}
    q = db.query(EventLog).filter(EventLog.created_at < cutoff)
    candidates = [e for e in q.all() if not any(e.event_type.startswith(x) for x in excluded)]
    return candidates

def candidate_telemetry(db: Session, retention_days: int):
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    return db.query(NetworkTelemetry).filter(NetworkTelemetry.created_at < cutoff).all()

def candidate_alerts(db: Session, retention_days: int):
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    return db.query(Alert).filter(Alert.created_at < cutoff, Alert.resolved == True).all()

def analyze_candidates(db: Session):
    events_days = int(get_setting(db, "retention_events_days", "30"))
    tel_days = int(get_setting(db, "retention_telemetry_days", "7"))
    alerts_days = int(get_setting(db, "retention_alerts_days", "90"))
    max_records = int(get_setting(db, "cleanup_max_records", "1000"))
    events = candidate_events(db, events_days)
    telemetry = candidate_telemetry(db, tel_days)
    alerts = candidate_alerts(db, alerts_days)
    total = len(events) + len(telemetry) + len(alerts)
    if total > max_records:
        pass
    return {
        "events": len(events),
        "telemetry": len(telemetry),
        "alerts": len(alerts),
        "total": total,
        "max_records": max_records,
    }

def record_run(db: Session, execution_type: str, dry_run: bool, scanned: int, deleted: int, details: str, status: str = "completed", error: str = None):
    run = CleanupRun(
        execution_type=execution_type,
        dry_run=dry_run,
        records_scanned=scanned,
        records_deleted=deleted,
        details=details,
        status=status,
        error_message=error,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

# Lock management
LOCK_KEY = "cleanup"
LOCK_TTL_SECONDS = 1200

def get_lock_ttl_seconds(db: Session) -> int:
    val = get_setting(db, "cleanup_lock_ttl_seconds", "1200")
    try:
        ttl = int(val)
        if ttl <= 0:
            return 1200
        return ttl
    except Exception:
        return 1200

def acquire_lock(db: Session, owner: str, ttl_seconds: int = LOCK_TTL_SECONDS) -> bool:
    now = datetime.utcnow()
    try:
        existing = db.query(CleanupLock).filter(CleanupLock.lock_key == LOCK_KEY).first()
        if existing and existing.expires_at < now:
            db.delete(existing)
            db.commit()
            existing = None
        if existing:
            return False
        db.add(CleanupLock(lock_key=LOCK_KEY, owner=owner, acquired_at=now, expires_at=now + timedelta(seconds=ttl_seconds)))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

def release_lock(db: Session, owner: str) -> bool:
    try:
        lock = db.query(CleanupLock).filter(CleanupLock.lock_key == LOCK_KEY, CleanupLock.owner == owner).first()
        if lock:
            db.delete(lock)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False

def is_lock_expired(db: Session) -> bool:
    lock = db.query(CleanupLock).filter(CleanupLock.lock_key == LOCK_KEY).first()
    if not lock:
        return True
    return lock.expires_at < datetime.utcnow()