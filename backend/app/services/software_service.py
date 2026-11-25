from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models.models import Device, SoftwareInventory

MAX_SOFTWARE_ITEMS = 5000


def _resolve_device(db: Session, ip: str):
    """Dispositivo asociado a una IP; si está archivado se usa solo como destino
    del inventario (nunca se reactiva el dispositivo)."""
    if not ip:
        return None
    return (
        db.query(Device)
        .filter(Device.ip == ip)
        .order_by(Device.deleted_at.is_(None).desc(), Device.id)
        .first()
    )


def persist_software(db: Session, items, default_ip: str = None) -> dict:
    """Persiste el inventario de software recibido del agente.

    Reglas:
    - Cada elemento queda asociado al dispositivo correcto (IP del equipo del agente
      o IP indicada por elemento).
    - Sin duplicados: se reutiliza la fila existente por nombre y solo se actualiza
      la versión si cambió. Las filas duplicadas generadas por versiones anteriores
      del agente se depuran en la misma operación.
    - Nunca se borra software de otros dispositivos ni se elimina un nombre que el
      agente ya no reporta (una respuesta incompleta no borra inventario).
    - Un error de software no invalida la persistencia de los dispositivos.
    """
    result = {"recibidos": 0, "guardados": 0, "actualizados": 0, "asociados": 0,
              "duplicados": 0, "sin_dispositivo": 0, "error": None}
    if not items:
        return result
    try:
        items = items[:MAX_SOFTWARE_ITEMS]
        result["recibidos"] = len(items)

        # Agrupa por dispositivo destino; ante nombres repetidos gana la última versión.
        grouped = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            name = (it.get("name") or "").strip()
            if not name:
                continue
            ip = (it.get("ip") or default_ip or "").strip() or None
            dev = _resolve_device(db, ip) if ip else None
            dev_id = dev.id if dev else None
            block = grouped.setdefault(dev_id, {"device": dev, "incoming": {}})
            block["incoming"][name] = (it.get("version") or "").strip() or None

        for dev_id, block in grouped.items():
            incoming = block["incoming"]
            if not incoming:
                continue
            names = list(incoming.keys())
            candidates = (
                db.query(SoftwareInventory)
                .filter(
                    SoftwareInventory.name.in_(names),
                    or_(SoftwareInventory.device_id == dev_id, SoftwareInventory.device_id.is_(None)),
                )
                .order_by(SoftwareInventory.id)
                .all()
            )
            by_name = {}
            for row in candidates:
                by_name.setdefault(row.name, []).append(row)

            for name, version in incoming.items():
                rows = by_name.get(name, [])
                if rows:
                    linked = [r for r in rows if r.device_id == dev_id]
                    canonical = linked[-1] if linked else rows[-1]
                    if canonical.device_id != dev_id:
                        canonical.device_id = dev_id
                        result["asociados"] += 1
                    if version and version != canonical.version:
                        canonical.version = version
                        result["actualizados"] += 1
                    for dup in rows:
                        if dup is not canonical:
                            db.delete(dup)
                            result["duplicados"] += 1
                else:
                    db.add(SoftwareInventory(device_id=dev_id, name=name, version=version, source="agent"))
                    result["guardados"] += 1

            if dev_id is None:
                result["sin_dispositivo"] += len(incoming)

        db.commit()
    except Exception as e:  # el software nunca debe romper el alta de dispositivos
        db.rollback()
        result["error"] = str(e)
    return result


def list_device_software(db: Session, device_id: int):
    return (
        db.query(SoftwareInventory)
        .filter(SoftwareInventory.device_id == device_id)
        .order_by(SoftwareInventory.name)
        .all()
    )
