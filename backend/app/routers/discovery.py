from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from ..discovery.discovery import discover_subnet, is_authorized
from ..services.device_service import upsert_device
from ..services.event_service import log_event
from ..services.settings_service import get_setting
from ..services.software_service import persist_software
from ..security.auth import require_api_key

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

# Contadores devueltos por /api/discovery/agent (documentación de negocio):
#  - recibidos:      dispositivos válidos recibidos (incluye archivados redescubiertos).
#  - rechazados:     dispositivos fuera de la subred autorizada.
#  - creados:        dispositivos nuevos guardados y confirmados.
#  - confirmados:    dispositivos que pasan a confirmed=True en esta ejecución
#                    (los nuevos + existentes sin confirmar que superan la validación).
#  - actualizados:   dispositivos existentes NO archivados cuyos datos se refrescaron.
#                    Puede solaparse con "confirmados" cuando un existente sin
#                    confirmar pasa a confirmado: la actualización no es un alta nueva.
#  - archivados:     dispositivos archivados redescubiertos que NO se reactivan.

@router.post("/start")
def start_discovery(db: Session = Depends(get_db)):
    subnet = get_setting(db, "authorized_subnet") or settings.authorized_subnet
    results = discover_subnet(subnet)
    devices = []
    active_ips = {r["ip"] for r in results}
    for r in results:
        if not is_authorized(r["ip"], subnet):
            continue
        from ..models.models import Device
        existing = db.query(Device).filter(Device.ip == r["ip"]).first()
        if existing and existing.deleted_at is not None:
            # archivado: no se reactiva automáticamente
            continue
        r["confirmed"] = True
        network = r.pop("network", None)
        dev = upsert_device(db, r)
        devices.append(dev.id)
        if network:
            from ..services.network_service import sync_interfaces
            sync_interfaces(db, dev, network)
    # Mark previously known devices without response as inactive (no deletion)
    from ..models.models import Device
    from ..services.device_service import set_status
    for dev in db.query(Device).all():
        if dev.deleted_at is not None:
            continue
        if is_authorized(dev.ip, subnet) and dev.ip not in active_ips:
            set_status(db, dev.id, "inactive")
            log_event(db, "availability", f"Dispositivo {dev.id} marcado inactivo tras descubrimiento", dev.id)
    log_event(db, "discovery", f"Descubrimiento completado: {len(devices)} dispositivos confirmados", None)
    return {"descubiertos": len(devices), "ids": devices, "sin_respuesta": len([d for d in db.query(Device).all() if d.deleted_at is None and is_authorized(d.ip, subnet) and d.ip not in active_ips])}

@router.post("/agent")
def agent_upload(payload: dict, db: Session = Depends(get_db), _=Depends(require_api_key)):
    devices = payload.get("devices", []) or []
    effective_subnet = get_setting(db, "authorized_subnet") or settings.authorized_subnet
    ids = []
    rejected = 0
    rejection_reasons = []
    received_ips = set()
    created_count = 0
    confirmed_count = 0
    updated_count = 0
    archived_count = 0

    from ..models.models import Device
    from ..services.device_service import set_status

    for d in devices:
        ip = d.get("ip", "")
        if not is_authorized(ip, effective_subnet):
            rejected += 1
            rejection_reasons.append("ip_fuera_de_subred_autorizada")
            log_event(db, "discovery", f"Dispositivo rechazado por subred no autorizada: {ip}", None)
            continue

        received_ips.add(ip)
        existing = db.query(Device).filter(Device.ip == ip).first()

        if existing and existing.deleted_at is not None:
            # Archivado: no se reactiva ni se actualiza automáticamente.
            archived_count += 1
            continue

        if existing:
            updated_count += 1
            if not existing.confirmed:
                confirmed_count += 1  # sin confirmar -> confirmado por validación
        else:
            created_count += 1
            confirmed_count += 1  # alta nueva validada -> confirmada

        d["confirmed"] = True
        network = d.pop("network", None)
        dev = upsert_device(db, d)
        ids.append(dev.id)
        if network:
            # Interfaces de red del equipo (solo el agente local puede reportarlas)
            from ..services.network_service import sync_interfaces
            try:
                sync_interfaces(db, dev, network)
            except Exception as e:
                db.rollback()
                log_event(db, "discovery", f"Interfaces de red no persistidas para {dev.ip}: {e}", dev.id)

    # Inventario de software: persistencia independiente de los dispositivos.
    sw = payload.get("software", []) or []
    sw_result = persist_software(db, sw, default_ip=payload.get("software_host_ip"))

    # Información de red del equipo del agente cuando no vino asociada a un dispositivo.
    agent_host = payload.get("agent_host") or {}
    host_ip = agent_host.get("ip")
    host_net = agent_host.get("network") or []
    if host_ip and host_net and host_ip not in received_ips:
        from ..services.network_service import sync_interfaces
        host_dev = db.query(Device).filter(Device.ip == host_ip, Device.deleted_at.is_(None)).first()
        if host_dev:
            try:
                sync_interfaces(db, host_dev, host_net)
            except Exception as e:
                db.rollback()
                log_event(db, "discovery", f"Interfaces de red no persistidas para {host_dev.ip}: {e}", host_dev.id)
            if agent_host.get("name") and not host_dev.name:
                host_dev.name = agent_host.get("name")
            if agent_host.get("os") and not host_dev.os_info:
                host_dev.os_info = agent_host.get("os")
            db.commit()

    # Mark previously known devices not reported in this run as inactive
    for dev in db.query(Device).all():
        if dev.deleted_at is not None:
            continue
        if is_authorized(dev.ip, effective_subnet) and dev.ip not in received_ips:
            set_status(db, dev.id, "inactive")

    log_event(
        db, "discovery",
        f"Agente procesó {len(ids)} dispositivos ({confirmed_count} confirmados, "
        f"{updated_count} actualizados, {archived_count} archivados sin reactivar) "
        f"y {rejected} rechazados en {effective_subnet}",
        None,
    )
    if sw_result.get("error"):
        log_event(db, "discovery", f"Inventario de software no persistido: {sw_result['error']}", None)

    return {
        "recibidos": len(ids) + archived_count,
        "rechazados": rejected,
        "motivos": rejection_reasons,
        "ids": ids,
        "software": sw_result["recibidos"],
        "software_guardados": sw_result["guardados"],
        "software_actualizados": sw_result["actualizados"],
        "software_asociados": sw_result["asociados"],
        "software_duplicados": sw_result["duplicados"],
        "software_error": sw_result["error"],
        "created_count": created_count,
        "confirmed_count": confirmed_count,
        "updated_count": updated_count,
        "archived_count": archived_count,
    }
