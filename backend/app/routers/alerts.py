from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Alert
from ..schemas.schemas import AlertOut
from ..services.audit_service import record_deletion

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("/", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.created_at.desc()).all()

@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.resolved = True
        db.commit()
    return {"id": alert_id, "resuelta": True}

@router.delete("/bulk")
def bulk_delete_alerts(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="Lista de IDs inválida")
    unique_ids = list(set(ids))
    alerts = db.query(Alert).filter(Alert.id.in_(unique_ids)).all()
    found = {a.id for a in alerts}
    missing = [i for i in unique_ids if i not in found]
    for a in alerts:
        db.delete(a)
    record_deletion(db, "alert", "bulk_delete", count=len(alerts), details={"ids": unique_ids, "missing": missing})
    db.commit()
    return {"eliminados": len(alerts), "no_encontrados": len(missing), "mensaje": f"{len(alerts)} alertas eliminadas"}

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    db.delete(alert)
    record_deletion(db, "alert", "delete", count=1, entity_id=alert_id)
    db.commit()
    return {"eliminados": 1, "mensaje": "Alerta eliminada"}