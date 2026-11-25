from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import SecurityAssessment, Device
from ..schemas.schemas import SecurityAssessmentIn
from ..services.event_service import log_event

router = APIRouter(prefix="/api/security", tags=["security"])

@router.post("/assess")
def assess(payload: SecurityAssessmentIn, db: Session = Depends(get_db)):
    sa = SecurityAssessment(**payload.model_dump())
    db.add(sa)
    db.commit()
    db.refresh(sa)
    log_event(db, "security", f"Evaluación de seguridad registrada para dispositivo {payload.device_id}", payload.device_id)
    return {"id": sa.id, "mensaje": "Evaluación registrada"}