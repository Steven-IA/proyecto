from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from ..security.auth import require_api_key
from ..services.settings_service import get_setting
from ..services.discovery_request_service import create_request, get_active_request, claim_next, complete_request, get_request

router = APIRouter(prefix="/api/discovery/requests", tags=["discovery-requests"])

@router.post("")
def create_discovery_request(db: Session = Depends(get_db)):
    subnet = get_setting(db, "authorized_subnet") or settings.authorized_subnet
    req, created = create_request(db, subnet)
    return {"id": req.id, "status": req.status, "created": created, "subnet": req.subnet}

@router.get("/active")
def active_request(db: Session = Depends(get_db)):
    req = get_active_request(db)
    if not req:
        return {"id": None, "status": "none"}
    return {"id": req.id, "status": req.status, "subnet": req.subnet, "discovered_count": req.discovered_count, "rejected_count": req.rejected_count, "error_message": req.error_message}

@router.post("/claim")
def claim_discovery_request(db: Session = Depends(get_db), _=Depends(require_api_key)):
    req = claim_next(db)
    if not req:
        return {"id": None, "status": "none"}
    return {"id": req.id, "status": req.status, "subnet": req.subnet}

@router.get("/{request_id}")
def get_discovery_request(request_id: str, db: Session = Depends(get_db)):
    req = get_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {
        "id": req.id,
        "status": req.status,
        "subnet": req.subnet,
        "discovered_count": req.discovered_count,
        "received_count": req.received_count,
        "confirmed_count": req.confirmed_count,
        "updated_count": req.updated_count,
        "archived_count": req.archived_count or 0,
        "rejected_count": req.rejected_count,
        "error_message": req.error_message,
        "created_at": req.created_at,
        "started_at": req.started_at,
        "finished_at": req.finished_at,
    }

@router.post("/{request_id}/complete")
def complete_discovery_request(request_id: str, payload: dict, db: Session = Depends(get_db), _=Depends(require_api_key)):
    status = payload.get("status", "completed")
    discovered_count = int(payload.get("discovered_count", 0))
    received_count = int(payload.get("received_count", 0))
    confirmed_count = int(payload.get("confirmed_count", 0))
    updated_count = int(payload.get("updated_count", 0))
    archived_count = int(payload.get("archived_count", 0))
    rejected_count = int(payload.get("rejected_count", 0))
    error_message = payload.get("error_message")
    req = complete_request(db, request_id, status, discovered_count, rejected_count, error_message)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    # update extra counts
    req.received_count = received_count
    req.confirmed_count = confirmed_count
    req.updated_count = updated_count
    req.archived_count = archived_count
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}