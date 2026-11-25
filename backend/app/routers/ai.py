from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Device, SecurityAssessment, AIAnalysis, Vulnerability
from ..config import settings
import os, json
from datetime import datetime

router = APIRouter(prefix="/api/ai", tags=["ai"])

FEATURES = ["firewall", "antivirus", "pending_updates", "os_age", "outdated", "vuln_apps", "excessive", "unnecessary", "unverified"]

def _provenance():
    return {
        "firewall": "evaluación manual",
        "antivirus": "evaluación manual",
        "pending_updates": "evaluación manual",
        "os_age": "evaluación manual",
        "outdated": "evaluación manual",
        "vuln_apps": "derivado de vulnerabilidades registradas",
        "excessive": "evaluación manual",
        "unnecessary": "evaluación manual",
        "unverified": "evaluación manual",
    }

def _assessment_to_features(sa: SecurityAssessment, db: Session, device_id: int):
    vuln_count = db.query(Vulnerability).filter(Vulnerability.device_id == device_id).count()
    return {
        "firewall": 1 if sa.firewall == "enabled" else 0,
        "antivirus": 1 if sa.antivirus == "enabled" else 0,
        "pending_updates": sa.pending_updates or 0,
        "os_age": sa.os_age_months or 0,
        "outdated": sa.outdated_software or 0,
        "vuln_apps": vuln_count if vuln_count > 0 else (sa.vulnerable_apps or 0),
        "excessive": 1 if sa.excessive_permissions else 0,
        "unnecessary": sa.unnecessary_services or 0,
        "unverified": sa.unverified_signatures or 0,
    }

def _validate_features(features):
    for f in FEATURES:
        if features.get(f) is None:
            return False, f
    return True, None

def _run_classifier(features):
    try:
        import torch
        import numpy as np
        from ..ai_models import SecurityClassifier
    except Exception as e:
        return None, None, str(e)
    path = os.path.join(settings.model_dir, "security_classifier.pth")
    if not os.path.exists(path):
        return None, None, "Pesos no disponibles"
    try:
        ckpt = torch.load(path, map_location="cpu")
        model = SecurityClassifier(input_dim=9)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        x = np.array([[features[f] for f in FEATURES]], dtype="float32")
        if ckpt.get("scaler_mean") is not None:
            mean = np.array(ckpt["scaler_mean"]); scale = np.array(ckpt["scaler_scale"])
            x = (x - mean) / scale
        t = torch.tensor(x, dtype=torch.float32)
        with torch.no_grad():
            out = model(t)
            probs = torch.softmax(out, dim=1)
            cls = int(out.argmax(1).item())
            confidences = [float(p) for p in probs[0].tolist()]
        labels = ["bajo", "medio", "alto"]
        return labels[cls], confidences, None
    except Exception as e:
        return None, None, str(e)

def _explain(features, predicted):
    reasons = []
    if features["firewall"] == 0:
        reasons.append("firewall deshabilitado")
    if features["antivirus"] == 0:
        reasons.append("antivirus deshabilitado")
    if features["pending_updates"] > 0:
        reasons.append(f"{features['pending_updates']} actualizaciones pendientes")
    if features["vuln_apps"] > 0:
        reasons.append(f"{features['vuln_apps']} aplicaciones vulnerables")
    if features["unverified"] > 0:
        reasons.append(f"{features['unverified']} firmas no verificadas")
    if not reasons:
        reasons.append("no se detectaron condiciones críticas evidentes")
    return f"Riesgo estimado: {predicted}. Factores: " + ", ".join(reasons) + "."

@router.post("/analyze-device/{device_id}")
def analyze_device(device_id: int, db: Session = Depends(get_db)):
    dev = db.query(Device).filter(Device.id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    if not dev.confirmed:
        raise HTTPException(status_code=400, detail="Dispositivo no confirmado")
    sa = db.query(SecurityAssessment).filter(SecurityAssessment.device_id == device_id).order_by(SecurityAssessment.created_at.desc()).first()
    if not sa:
        # no_data
        analysis = AIAnalysis(device_id=device_id, model_name="security_classifier", input_features=json.dumps({}), provenance=json.dumps({}), predicted_class="no_data", probabilities=None, explanation="No hay evaluación de seguridad para este dispositivo.", status="no_data")
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return {"id": analysis.id, "device_id": device_id, "status": "no_data", "predicted_class": "no_data", "explanation": analysis.explanation}
    features = _assessment_to_features(sa, db, device_id)
    ok, missing = _validate_features(features)
    if not ok:
        analysis = AIAnalysis(device_id=device_id, model_name="security_classifier", input_features=json.dumps(features), provenance=json.dumps(_provenance()), predicted_class="no_data", probabilities=None, explanation=f"Faltan datos: {missing}", status="no_data")
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return {"id": analysis.id, "device_id": device_id, "status": "no_data", "predicted_class": "no_data", "explanation": analysis.explanation}
    predicted, probs, err = _run_classifier(features)
    if err:
        analysis = AIAnalysis(device_id=device_id, model_name="security_classifier", input_features=json.dumps(features), provenance=json.dumps(_provenance()), predicted_class="error", probabilities=None, explanation=err, status="error")
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return {"id": analysis.id, "device_id": device_id, "status": "error", "predicted_class": "error", "explanation": err}
    explanation = _explain(features, predicted)
    analysis = AIAnalysis(device_id=device_id, model_name="security_classifier", input_features=json.dumps(features), provenance=json.dumps(_provenance()), predicted_class=predicted, probabilities=json.dumps(probs), explanation=explanation, status="completed")
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return {"id": analysis.id, "device_id": device_id, "status": "completed", "predicted_class": predicted, "probabilities": probs, "explanation": explanation}

@router.get("/analyses")
def list_analyses(device_id: int = None, db: Session = Depends(get_db)):
    q = db.query(AIAnalysis)
    if device_id:
        q = q.filter(AIAnalysis.device_id == device_id)
    rows = q.order_by(AIAnalysis.created_at.desc()).all()
    return [{"id": r.id, "device_id": r.device_id, "model_name": r.model_name, "predicted_class": r.predicted_class, "status": r.status, "explanation": r.explanation, "probabilities": json.loads(r.probabilities) if r.probabilities else None, "input_features": json.loads(r.input_features) if r.input_features else None, "provenance": json.loads(r.provenance) if r.provenance else None, "created_at": r.created_at} for r in rows]

@router.get("/summary")
def ai_summary(db: Session = Depends(get_db)):
    rows = db.query(AIAnalysis).all()
    counts = {"bajo": 0, "medio": 0, "alto": 0, "no_data": 0, "error": 0}
    for r in rows:
        if r.predicted_class in counts:
            counts[r.predicted_class] += 1
    return {"total_analyses": len(rows), "counts": counts}