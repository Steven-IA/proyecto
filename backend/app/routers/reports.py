from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from ..models.models import Device, Alert, Vulnerability
import os, json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/api/reports", tags=["reports"])

def _metrics():
    out = {}
    for name in ("network_transformer", "security_classifier"):
        path = os.path.join(settings.model_dir, f"{name}_metrics.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    out[name] = json.load(f)
            except Exception:
                out[name] = None
        else:
            out[name] = None
    return out

@router.post("/generate")
def generate_report(db: Session = Depends(get_db)):
    os.makedirs(settings.report_dir, exist_ok=True)
    path = os.path.join(settings.report_dir, "reporte_sentinelai.pdf")

    confirmed = db.query(Device).filter(Device.confirmed == True).all()
    inactive_known = [d for d in confirmed if d.status == "inactive"]
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(20).all()
    vulns = db.query(Vulnerability).all()
    metrics = _metrics()

    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 50

    def line(text, size=10, bold=False):
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 50
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(50, y, text[:110])
        y -= 14

    line("SentinelAI - Reporte de Seguridad", 16, True)
    line(f"Fecha de generación: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    line("")

    line("Resumen ejecutivo", 12, True)
    line(f"Dispositivos confirmados: {len(confirmed)}")
    line(f"Dispositivos confirmados inactivos: {len(inactive_known)}")
    line(f"Alertas registradas: {len(alerts)}")
    line(f"Vulnerabilidades registradas: {len(vulns)}")
    line("")

    line("Dispositivos confirmados", 12, True)
    if not confirmed:
        line("No hay dispositivos confirmados.")
    else:
        for d in confirmed[:50]:
            line(f"- {d.ip} | {d.hostname or 'No disponible'} | {d.device_type or 'desconocido'} | {d.status} | {d.vendor or 'Desconocido'}")
    line("")

    line("Alertas recientes", 12, True)
    if not alerts:
        line("No hay alertas registradas.")
    else:
        for a in alerts:
            line(f"- [{a.severity}] {a.message} ({a.created_at})")
    line("")

    line("Vulnerabilidades registradas", 12, True)
    if not vulns:
        line("No hay vulnerabilidades registradas.")
    else:
        for v in vulns[:50]:
            line(f"- {v.cve_id} | {v.software or 'No disponible'} | {v.severity or 'N/A'} | {v.verification_level}")
    line("")

    line("Estado de modelos de IA", 12, True)
    for name in ("network_transformer", "security_classifier"):
        m = metrics.get(name)
        if m:
            line(f"- {name}: precisión {m.get('accuracy')}, validación {m.get('val_accuracy')}")
            line(f"  Dataset: {m.get('dataset')}")
            line(f"  Limitación: {m.get('limitation')}")
        else:
            line(f"- {name}: sin métricas disponibles")
    line("")

    line("Recomendaciones", 12, True)
    if not confirmed:
        line("- Ejecutar un descubrimiento autorizado para obtener inventario real.")
    else:
        if len(inactive_known) > 0:
            line("- Revisar dispositivos confirmados que están inactivos.")
        if len(vulns) > 0:
            line("- Revisar vulnerabilidades potenciales y confirmar inventario de software.")
        if not vulns and confirmed:
            line("- Mantener actualizaciones y monitoreo continuo.")
    line("")

    line("Limitaciones", 12, True)
    line("- Los datos provienen de descubrimiento autorizado y pueden estar incompletos.")
    line("- Los modelos usan datasets sintéticos; no son evidencia de amenazas reales.")
    line("- Las vulnerabilidades sin inventario de software no se afirman como confirmadas.")

    c.save()
    return {"archivo": os.path.basename(path), "mensaje": "Reporte generado"}

@router.get("/download")
def download_report(filename: str = Query("reporte_sentinelai.pdf")):
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    path = os.path.join(settings.report_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return FileResponse(path, filename=filename, media_type="application/pdf")