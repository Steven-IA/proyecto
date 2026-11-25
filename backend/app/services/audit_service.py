from sqlalchemy.orm import Session
from ..models.models import DeletionAudit
import json

def record_deletion(db: Session, entity_type: str, action: str, count: int = 0, entity_id=None, details=None):
    audit = DeletionAudit(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        count=count,
        details=json.dumps(details) if details is not None else None,
    )
    db.add(audit)
    # Do not commit here; let caller control transaction.
    return audit