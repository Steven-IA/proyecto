from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Vulnerability, Device
from ..vuln.vuln import scan_software
from ..services.event_service import log_event
from ..services.audit_service import record_deletion

router = APIRouter(prefix="/api/vulnerabilities", tags=["vulnerabilities"])

@router.get("/")
def list_vulns(db: Session = Depends(get_db)):
    return db.query(Vulnerability).all()

@router.post("/scan/{device_id}")
def scan_device(device_id: int, db: Session = Depends(get_db)):
    dev = db.query(Device).filter(Device.id == device_id).first()
    if not dev:
        return {"error": "Dispositivo no encontrado"}
    from ..models.models import SoftwareInventory
    sw_items = db.query(SoftwareInventory).filter((SoftwareInventory.device_id == device_id) | (SoftwareInventory.device_id.is_(None))).all()
    if not sw_items:
        log_event(db, "vulnerability", f"Escaneo omitido: sin inventario de software para dispositivo {device_id}", device_id)
        return {"device_id": device_id, "mensaje": "Inventario de software no disponible", "encontradas": 0}
    total = 0
    for sw in sw_items[:20]:
        results = scan_software(device_id, sw.name, sw.version or "unknown")
        for r in results:
            db.add(Vulnerability(device_id=device_id, **{k: r[k] for k in ["cve_id","software","version","severity","description","recommendation","fixed_version","verification_level"]}))
        total += len(results)
    db.commit()
    log_event(db, "vulnerability", f"Escaneo completado para dispositivo {device_id}: {total} hallazgos", device_id)
    return {"device_id": device_id, "encontradas": total}

@router.delete("/bulk")
def bulk_delete_vulnerabilities(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="Lista de IDs inválida")
    unique_ids = list(set(ids))
    vulns = db.query(Vulnerability).filter(Vulnerability.id.in_(unique_ids)).all()
    found = {v.id for v in vulns}
    missing = [i for i in unique_ids if i not in found]
    for v in vulns:
        db.delete(v)
    record_deletion(db, "vulnerability", "bulk_delete", count=len(vulns), details={"ids": unique_ids, "missing": missing})
    db.commit()
    return {"eliminados": len(vulns), "no_encontrados": len(missing), "mensaje": f"{len(vulns)} vulnerabilidades eliminadas"}

@router.delete("/{vuln_id}")
def delete_vulnerability(vuln_id: int, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerabilidad no encontrada")
    db.delete(vuln)
    record_deletion(db, "vulnerability", "delete", count=1, entity_id=vuln_id)
    db.commit()
    return {"eliminados": 1, "mensaje": "Vulnerabilidad eliminada"}