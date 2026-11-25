from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import TrainingInfo
from ..config import settings
import os, json

router = APIRouter(prefix="/api/training", tags=["training"])

MODEL_NAMES = ["network_transformer", "security_classifier"]

def _load_status(name):
    weight_path = os.path.join(settings.model_dir, f"{name}.pth")
    metrics_path = os.path.join(settings.model_dir, f"{name}_metrics.json")
    weights_available = os.path.exists(weight_path)
    metrics_available = os.path.exists(metrics_path)
    metrics = None
    if metrics_available:
        try:
            with open(metrics_path) as f:
                metrics = json.load(f)
        except Exception:
            metrics = None
    loaded = False
    error = None
    if weights_available:
        try:
            import torch
            from ..ai_models import NetworkTransformer, SecurityClassifier
            if name == "network_transformer":
                model = NetworkTransformer(input_dim=8)
            else:
                model = SecurityClassifier(input_dim=9)
            ckpt = torch.load(weight_path, map_location="cpu")
            model.load_state_dict(ckpt["state_dict"])
            model.eval()
            # prueba de inferencia
            import numpy as np
            dim = 8 if name == "network_transformer" else 9
            with torch.no_grad():
                model(torch.tensor([[1.0]*dim], dtype=torch.float32))
            loaded = True
        except Exception as e:
            error = str(e)
    if not weights_available:
        status = "sin_entrenar"
    elif error:
        status = "error_carga"
    elif loaded and metrics_available:
        status = "disponible"
    elif loaded:
        status = "cargado"
    else:
        status = "entrenado_no_disponible"
    return {
        "model": name,
        "weights_available": weights_available,
        "metrics_available": metrics_available,
        "loaded": loaded,
        "status": status,
        "error": error,
        "metrics": metrics,
    }

@router.get("/metrics")
def training_metrics(db: Session = Depends(get_db)):
    return [_load_status(name) for name in MODEL_NAMES]

@router.get("/status")
def training_status():
    return [_load_status(name) for name in MODEL_NAMES]