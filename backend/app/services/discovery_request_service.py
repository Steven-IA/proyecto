import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.models import DiscoveryRequest

PENDING_TIMEOUT_MINUTES = 10
RUNNING_TIMEOUT_MINUTES = 5

def expire_stale(db: Session):
    now = datetime.utcnow()
    # pending too old
    for req in db.query(DiscoveryRequest).filter(DiscoveryRequest.status == "pending").all():
        if req.created_at and now - req.created_at > timedelta(minutes=PENDING_TIMEOUT_MINUTES):
            req.status = "error"
            req.error_message = "Tiempo de espera agotado (pendiente)"
            req.finished_at = now
    # running too old
    for req in db.query(DiscoveryRequest).filter(DiscoveryRequest.status == "running").all():
        if req.started_at and now - req.started_at > timedelta(minutes=RUNNING_TIMEOUT_MINUTES):
            req.status = "error"
            req.error_message = "Tiempo de espera agotado (ejecución)"
            req.finished_at = now
    db.commit()

def get_active_request(db: Session):
    expire_stale(db)
    return db.query(DiscoveryRequest).filter(DiscoveryRequest.status.in_(["pending", "running"])).order_by(DiscoveryRequest.created_at.desc()).first()

def create_request(db: Session, subnet: str):
    expire_stale(db)
    active = get_active_request(db)
    if active:
        return active, False
    req = DiscoveryRequest(id=str(uuid.uuid4()), status="pending", subnet=subnet)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req, True

def claim_next(db: Session):
    expire_stale(db)
    candidate = db.query(DiscoveryRequest).filter(DiscoveryRequest.status == "pending").order_by(DiscoveryRequest.created_at.asc()).first()
    if not candidate:
        return None
    rows = db.query(DiscoveryRequest).filter(DiscoveryRequest.id == candidate.id, DiscoveryRequest.status == "pending").update(
        {"status": "running", "started_at": datetime.utcnow()}, synchronize_session=False
    )
    db.commit()
    if rows == 0:
        return None
    return db.query(DiscoveryRequest).filter(DiscoveryRequest.id == candidate.id).first()

def complete_request(db: Session, request_id: str, status: str, discovered_count: int = 0, rejected_count: int = 0, error_message: str = None):
    expire_stale(db)
    req = db.query(DiscoveryRequest).filter(DiscoveryRequest.id == request_id).first()
    if not req:
        return None
    if req.status != "running":
        return req  # invalid transition; do not change
    if status not in ("completed", "error"):
        return req
    req.status = status
    req.discovered_count = discovered_count
    req.rejected_count = rejected_count
    req.error_message = error_message
    req.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req

def get_request(db: Session, request_id: str):
    expire_stale(db)
    return db.query(DiscoveryRequest).filter(DiscoveryRequest.id == request_id).first()