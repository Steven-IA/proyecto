from sqlalchemy.orm import Session
from ..models.models import EventLog

def log_event(db: Session, event_type: str, message: str, device_id=None):
    ev = EventLog(event_type=event_type, message=message, device_id=device_id)
    db.add(ev)
    db.commit()
    return ev

def list_events(db: Session, event_type=None, device_id=None, q=None):
    query = db.query(EventLog)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    if device_id:
        query = query.filter(EventLog.device_id == device_id)
    if q:
        query = query.filter(EventLog.message.ilike(f"%{q}%"))
    return query.order_by(EventLog.created_at.desc()).all()