from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.event_service import list_events
from ..models.models import EventLog
from ..services.audit_service import record_deletion

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/")
def get_history(event_type: str = None, device_id: int = None, q: str = None, db: Session = Depends(get_db)):
    events = list_events(db, event_type=event_type, device_id=device_id, q=q)
    return [{"id": e.id, "event_type": e.event_type, "device_id": e.device_id, "message": e.message, "created_at": e.created_at} for e in events]

@router.delete("/bulk")
def bulk_delete_events(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="Lista de IDs inválida")
    unique_ids = list(set(ids))
    events = db.query(EventLog).filter(EventLog.id.in_(unique_ids)).all()
    found = {e.id for e in events}
    missing = [i for i in unique_ids if i not in found]
    for e in events:
        db.delete(e)
    record_deletion(db, "event", "bulk_delete", count=len(events), details={"ids": unique_ids, "missing": missing})
    db.commit()
    return {"eliminados": len(events), "no_encontrados": len(missing), "mensaje": f"{len(events)} eventos eliminados"}

@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(EventLog).filter(EventLog.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(ev)
    record_deletion(db, "event", "delete", count=1, entity_id=event_id)
    db.commit()
    return {"eliminados": 1, "mensaje": "Evento eliminado"}