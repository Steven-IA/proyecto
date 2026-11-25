from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import InferenceIn
import os, json
from ..config import settings

router = APIRouter(prefix="/api/inference", tags=["inference"])

def _load_network():
    path = os.path.join(settings.model_dir, "network_transformer.pth")
    if not os.path.exists(path):
        return None, None
    try:
        import torch
        from ..ai_models import NetworkTransformer
    except Exception:
        return None, None
    ckpt = torch.load(path, map_location="cpu")
    model = NetworkTransformer(input_dim=8)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt

def _load_security():
    path = os.path.join(settings.model_dir, "security_classifier.pth")
    if not os.path.exists(path):
        return None, None
    try:
        import torch
        from ..ai_models import SecurityClassifier
    except Exception:
        return None, None
    ckpt = torch.load(path, map_location="cpu")
    model = SecurityClassifier(input_dim=9)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt

@router.post("/anomaly")
def anomaly_inference(payload: InferenceIn):
    model, ckpt = _load_network()
    if model is None:
        return {"error": "Modelo no entrenado", "disponible": False}
    import numpy as np
    import torch
    x = np.array(payload.features, dtype="float32").reshape(1, -1)
    if ckpt.get("scaler_mean") is not None:
        mean = np.array(ckpt["scaler_mean"]); scale = np.array(ckpt["scaler_scale"])
        x = (x - mean) / scale
    t = torch.tensor(x, dtype=torch.float32)
    with torch.no_grad():
        out = model(t)
        probs = torch.softmax(out, dim=1)
        cls = int(out.argmax(1).item())
        score = float(probs[0][1].item())
    return {"modelo": "network_transformer", "clasificacion": "anómalo" if cls == 1 else "normal", "puntuacion_anomalia": score, "disponible": True}

@router.post("/risk")
def risk_inference(payload: InferenceIn):
    model, ckpt = _load_security()
    if model is None:
        return {"error": "Modelo no entrenado", "disponible": False}
    import numpy as np
    import torch
    x = np.array(payload.features, dtype="float32").reshape(1, -1)
    if ckpt.get("scaler_mean") is not None:
        mean = np.array(ckpt["scaler_mean"]); scale = np.array(ckpt["scaler_scale"])
        x = (x - mean) / scale
    t = torch.tensor(x, dtype=torch.float32)
    with torch.no_grad():
        out = model(t)
        probs = torch.softmax(out, dim=1)
        cls = int(out.argmax(1).item())
        conf = float(probs[0][cls].item())
    labels = ["bajo", "medio", "alto"]
    return {"modelo": "security_classifier", "riesgo": labels[cls], "confianza": conf, "disponible": True}