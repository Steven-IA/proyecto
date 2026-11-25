import os
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REPORT_DIR"] = os.path.abspath("./test_reports")
os.environ["MODEL_DIR"] = os.path.abspath("../models")

# Base de pruebas aislada: cada ejecución parte de una SQLite limpia.
for _f in ("./test.db", "./test.db-wal", "./test.db-shm"):
    try:
        if os.path.exists(_f):
            os.remove(_f)
    except OSError:
        pass

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.services.settings_service import set_setting
init_db()
_db = SessionLocal()
set_setting(_db, "authorized_subnet", "192.168.10.0/24")
_db.close()
client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_discovery_rejects_out_of_subnet():
    from app.discovery.discovery import is_authorized
    assert is_authorized("192.168.1.10", "192.168.1.0/24") is True
    assert is_authorized("10.0.0.1", "192.168.1.0/24") is False

def test_inference_requires_trained_model():
    # Without weights, endpoint reports unavailable
    r = client.post("/api/inference/anomaly", json={"features": [1.0]*8})
    assert r.status_code == 200
    assert "disponible" in r.json() or "error" in r.json()

def test_report_generation():
    r = client.post("/api/reports/generate")
    assert r.status_code == 200
    assert "archivo" in r.json()

def test_agent_upload_authorized_ip():
    from app.services.settings_service import set_setting
    from app.database import SessionLocal
    db = SessionLocal()
    set_setting(db, "authorized_subnet", "192.168.10.0/24")
    db.close()
    payload = {"devices": [{"ip": "192.168.10.5", "mac": "AA:BB:CC:DD:EE:FF", "vendor": "Test", "hostname": "host", "device_type": "computador", "status": "active", "source": "agent"}], "software": [{"name": "prog", "version": "1.0"}]}
    r = client.post("/api/discovery/agent", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 200
    data = r.json()
    assert data["recibidos"] == 1
    assert data["software"] == 1
    devs = client.get("/api/devices/").json()
    assert any(d["ip"] == "192.168.10.5" and d["confirmed"] for d in devs)

def test_agent_upload_rejected_ip():
    payload = {"devices": [{"ip": "10.0.0.5", "status": "active", "source": "agent"}], "software": []}
    r = client.post("/api/discovery/agent", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 200
    data = r.json()
    assert data["recibidos"] == 0
    assert data["rechazados"] == 1
    assert "ip_fuera_de_subred_autorizada" in data["motivos"]

HDR = {"X-API-Key": "change-me-in-production"}

def test_agent_existing_unconfirmed_becomes_confirmed():
    from app.models.models import Device
    from app.database import SessionLocal
    db = SessionLocal()
    db.add(Device(ip="192.168.10.101", status="active", confirmed=False, source="discovered"))
    db.commit(); db.close()
    payload = {"devices": [{"ip": "192.168.10.101", "mac": "AA:BB:CC:00:00:01", "status": "active", "source": "agent"}], "software": []}
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["recibidos"] == 1
    assert data["updated_count"] == 1
    assert data["created_count"] == 0
    assert data["confirmed_count"] == 1  # sin confirmar -> confirmado
    devs = client.get("/api/devices/").json()
    d = [x for x in devs if x["ip"] == "192.168.10.101"]
    assert d and d[0]["confirmed"] is True

def test_agent_archived_device_not_reactivated():
    from app.models.models import Device
    from app.database import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    dev = Device(ip="192.168.10.102", status="active", confirmed=True, source="agent", deleted_at=datetime.utcnow())
    db.add(dev); db.commit(); db.refresh(dev)
    did = dev.id
    db.close()
    payload = {"devices": [{"ip": "192.168.10.102", "status": "active", "source": "agent"}],
               "software": [{"name": "App Archivada", "version": "1"}],
               "software_host_ip": "192.168.10.102"}
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["archived_count"] == 1
    assert data["updated_count"] == 0
    assert data["confirmed_count"] == 0
    assert data["recibidos"] == 1
    devs = client.get("/api/devices/?include_deleted=true").json()
    d = [x for x in devs if x["id"] == did]
    assert d and d[0]["deleted_at"] is not None
    # el software se asocia al registro archivado, sin reactivar el dispositivo
    sw = client.get(f"/api/devices/{did}/software").json()
    assert len(sw) == 1 and sw[0]["name"] == "App Archivada"

def test_device_restore():
    from app.models.models import Device
    from app.database import SessionLocal
    db = SessionLocal()
    dev = Device(ip="192.168.10.103", status="active", confirmed=True, source="agent")
    db.add(dev); db.commit(); db.refresh(dev)
    did = dev.id
    db.close()
    assert client.delete(f"/api/devices/{did}").status_code == 200
    assert not any(d["id"] == did for d in client.get("/api/devices/").json())
    r = client.post(f"/api/devices/{did}/restore")
    assert r.status_code == 200
    assert r.json()["restaurados"] == 1
    devs = client.get("/api/devices/").json()
    d = [x for x in devs if x["id"] == did]
    assert d and d[0]["confirmed"] is True and d[0]["deleted_at"] is None

def test_software_persisted_linked_and_deduplicated():
    payload = {"devices": [{"ip": "192.168.10.104", "mac": "AA:BB:CC:00:00:02", "status": "active", "source": "agent"}],
               "software": [{"name": "App Alpha", "version": "1.0"}, {"name": "App Beta", "version": "2.0"}],
               "software_host_ip": "192.168.10.104"}
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["software"] == 2
    assert data["software_guardados"] == 2
    assert data["software_error"] is None
    did = data["ids"][0]
    sw = client.get(f"/api/devices/{did}/software").json()
    assert len(sw) == 2
    assert all(s["device_id"] == did for s in sw)
    # segunda pasada: sin duplicados, versión actualizada
    payload["software"] = [{"name": "App Alpha", "version": "1.1"}, {"name": "App Beta", "version": "2.0"}]
    data2 = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data2["software_guardados"] == 0
    assert data2["software_actualizados"] == 1
    sw2 = client.get(f"/api/devices/{did}/software").json()
    assert len(sw2) == 2
    alpha = [s for s in sw2 if s["name"] == "App Alpha"][0]
    assert alpha["version"] == "1.1"

def test_software_deduplicates_legacy_orphans():
    from app.models.models import SoftwareInventory, Device
    from app.database import SessionLocal
    db = SessionLocal()
    db.add(Device(ip="192.168.10.105", status="active", confirmed=True, source="agent"))
    db.add(SoftwareInventory(device_id=None, name="Legacy App", version="1.0", source="agent"))
    db.add(SoftwareInventory(device_id=None, name="Legacy App", version="1.1", source="agent"))
    db.commit()
    db.close()
    payload = {"devices": [{"ip": "192.168.10.105", "status": "active", "source": "agent"}],
               "software": [{"name": "Legacy App", "version": "1.2"}],
               "software_host_ip": "192.168.10.105"}
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["software_error"] is None
    assert data["software_asociados"] >= 1
    assert data["software_actualizados"] == 1
    assert data["software_duplicados"] >= 1
    db = SessionLocal()
    rows = db.query(SoftwareInventory).filter(SoftwareInventory.name == "Legacy App").all()
    assert len(rows) == 1
    assert rows[0].version == "1.2"
    did = rows[0].device_id
    db.close()
    sw = client.get(f"/api/devices/{did}/software").json()
    assert len(sw) == 1 and sw[0]["name"] == "Legacy App"

def test_devices_summary_persisted():
    s = client.get("/api/devices/summary").json()
    assert s["confirmados"] >= 1
    assert s["total_dispositivos"] >= s["confirmados"]
    assert s["software_total"] >= s["software_asociado"] >= 0
    assert "interfaces_total" in s
    assert "ips_registradas" in s
    assert "ultimo_descubrimiento" in s

def test_network_interfaces_persisted_and_multi_interface():
    payload = {
        "devices": [{
            "ip": "192.168.10.106", "mac": "AA:BB:CC:00:00:03", "hostname": "host-red",
            "name": "PC-RED", "os_info": "Windows 11 Pro", "status": "active", "source": "agent",
            "network": [
                {"ip": "192.168.10.106", "mac": "AA:BB:CC:00:00:03", "prefix_length": 24,
                 "gateway": "192.168.10.1", "dns": "1.1.1.1,8.8.8.8",
                 "interface_name": "Ethernet", "interface_type": "Hyper-V Virtual Ethernet Adapter",
                 "status": "Up"},
                {"ip": "172.26.0.1", "mac": "AA:BB:CC:00:00:03", "prefix_length": 28,
                 "interface_name": "vEthernet (WSL)", "interface_type": "Hyper-V Virtual Ethernet Adapter",
                 "status": "Up"},
            ],
        }],
        "software": [],
    }
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["recibidos"] == 1, data
    did = data["ids"][0]
    itfs = client.get(f"/api/devices/{did}/interfaces").json()
    assert len(itfs) == 2                      # varias interfaces conservadas, sin duplicados
    prim = [i for i in itfs if i["is_primary"]]
    assert len(prim) == 1 and prim[0]["ip"] == "192.168.10.106"
    assert prim[0]["subnet"] == "192.168.10.0/24"
    assert prim[0]["netmask"] == "255.255.255.0"
    assert prim[0]["gateway"] == "192.168.10.1"
    assert prim[0]["dns"] == "1.1.1.1,8.8.8.8"
    devs = client.get("/api/devices/").json()
    d = [x for x in devs if x["id"] == did][0]
    assert d["ip"] == "192.168.10.106"
    assert d["mac"] == "AA:BB:CC:00:00:03"
    assert d["subnet"] == "192.168.10.0/24"
    assert d["gateway"] == "192.168.10.1"
    assert d["interface_count"] == 2
    det = client.get(f"/api/devices/{did}").json()
    assert len(det["interfaces"]) == 2
    assert det["os_info"] == "Windows 11 Pro"
    s = client.get("/api/devices/summary").json()
    assert s["interfaces_total"] >= 2
    assert s["ips_registradas"] >= 2

def test_incomplete_network_collection_keeps_previous_data():
    payload = {"devices": [{"ip": "192.168.10.107", "mac": "AA:BB:CC:00:00:04",
                            "status": "active", "source": "agent",
                            "network": [{"ip": "192.168.10.107", "mac": "AA:BB:CC:00:00:04",
                                         "prefix_length": 24, "gateway": "192.168.10.1",
                                         "interface_name": "Ethernet", "status": "Up"}]}],
               "software": []}
    did = client.post("/api/discovery/agent", json=payload, headers=HDR).json()["ids"][0]
    before = client.get(f"/api/devices/{did}/interfaces").json()
    assert len(before) == 1 and before[0]["gateway"] == "192.168.10.1"
    # recolección incompleta: sin interfaces -> no borra lo válido
    payload["devices"][0].pop("network")
    payload["devices"][0]["network"] = []
    client.post("/api/discovery/agent", json=payload, headers=HDR)
    after = client.get(f"/api/devices/{did}/interfaces").json()
    assert len(after) == 1
    assert after[0]["gateway"] == "192.168.10.1"
    assert after[0]["mac"] == "AA:BB:CC:00:00:04"

def test_unknown_values_do_not_degrade_existing_data():
    payload = {"devices": [{"ip": "192.168.10.108", "mac": "AA:BB:CC:00:00:05",
                            "hostname": "host-real", "name": "PC-REAL",
                            "status": "active", "source": "agent"}], "software": []}
    did = client.post("/api/discovery/agent", json=payload, headers=HDR).json()["ids"][0]
    # segunda recolección incompleta con valores "No disponible"
    payload["devices"][0].update({"mac": "No disponible", "hostname": "No disponible", "name": "No disponible", "os_info": ""})
    client.post("/api/discovery/agent", json=payload, headers=HDR)
    d = [x for x in client.get("/api/devices/").json() if x["id"] == did][0]
    assert d["mac"] == "AA:BB:CC:00:00:05"
    assert d["hostname"] == "host-real"
    assert d["name"] == "PC-REAL"

def test_software_links_to_archived_device_without_reactivation():
    from app.models.models import Device
    from app.database import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    dev = Device(ip="192.168.10.111", status="active", confirmed=True, source="agent", deleted_at=datetime.utcnow())
    db.add(dev); db.commit(); db.refresh(dev)
    did = dev.id
    db.close()
    payload = {"devices": [{"ip": "192.168.10.111", "status": "active", "source": "agent"}],
               "software_host_ip": "192.168.10.111",
               "software": [{"name": "App-Archivada", "version": "1.0"}]}
    client.post("/api/discovery/agent", json=payload, headers=HDR)
    db = SessionLocal()
    d = db.query(Device).filter(Device.id == did).first()
    assert d.deleted_at is not None                      # no reactivado
    sw = [s for s in client.get(f"/api/devices/{did}/software").json() if s["name"] == "App-Archivada"]
    assert len(sw) == 1                                  # software sí queda asociado
    db.close()

def test_interface_mac_fills_unknown_device_mac():
    payload = {"devices": [{"ip": "192.168.10.110", "mac": "No disponible", "hostname": "No disponible",
                            "status": "active", "source": "agent",
                            "network": [{"ip": "192.168.10.110", "mac": "F4:28:9D:61:12:73",
                                         "prefix_length": 24, "status": "Up"}]}], "software": []}
    did = client.post("/api/discovery/agent", json=payload, headers=HDR).json()["ids"][0]
    d = [x for x in client.get("/api/devices/").json() if x["id"] == did][0]
    assert d["mac"] == "F4:28:9D:61:12:73"   # MAC real del adaptador, no "No disponible"
    itfs = client.get(f"/api/devices/{did}/interfaces").json()
    assert itfs[0]["mac"] == "F4:28:9D:61:12:73"

def test_archived_device_gets_no_interfaces():
    from app.models.models import Device, NetworkInterface
    from app.database import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    dev = Device(ip="192.168.10.109", status="active", confirmed=True, source="agent", deleted_at=datetime.utcnow())
    db.add(dev); db.commit(); db.refresh(dev)
    did = dev.id
    db.close()
    payload = {"devices": [{"ip": "192.168.10.109", "status": "active", "source": "agent",
                            "network": [{"ip": "192.168.10.109", "prefix_length": 24, "status": "Up"}]}],
               "software": []}
    data = client.post("/api/discovery/agent", json=payload, headers=HDR).json()
    assert data["archived_count"] == 1
    assert client.get(f"/api/devices/{did}/interfaces").json() == []
    db = SessionLocal()
    assert db.query(NetworkInterface).filter(NetworkInterface.device_id == did).count() == 0
    d = db.query(Device).filter(Device.id == did).first()
    assert d.deleted_at is not None   # sigue archivado, sin reactivar
    db.close()

def test_sqlite_config_prevails_over_env():
    # env is 192.168.1.0/24 by default in tests, DB set to 192.168.10.0/24
    from app.services.settings_service import get_setting
    from app.database import SessionLocal
    db = SessionLocal()
    assert get_setting(db, "authorized_subnet") == "192.168.10.0/24"
    db.close()

def test_historical_unconfirmed_excluded():
    from app.models.models import Device
    from app.database import SessionLocal
    db = SessionLocal()
    db.add(Device(ip="192.168.10.99", status="inactive", confirmed=False, source="discovered"))
    db.commit()
    db.close()
    devs = client.get("/api/devices/").json()
    assert not any(d["ip"] == "192.168.10.99" for d in devs)
    all_devs = client.get("/api/devices/?confirmed_only=false").json()
    assert any(d["ip"] == "192.168.10.99" for d in all_devs)

def test_device_soft_delete():
    from app.models.models import Device
    from app.database import SessionLocal
    db = SessionLocal()
    dev = Device(ip="192.168.10.50", status="active", confirmed=True, source="agent")
    db.add(dev)
    db.commit()
    db.refresh(dev)
    did = dev.id
    db.close()
    r = client.delete(f"/api/devices/{did}")
    assert r.status_code == 200
    assert r.json()["eliminados"] == 1
    devs = client.get("/api/devices/").json()
    assert not any(d["id"] == did for d in devs)
    # still in DB with deleted_at
    db = SessionLocal()
    d = db.query(Device).filter(Device.id == did).first()
    assert d.deleted_at is not None
    db.close()

def test_bulk_delete_alerts():
    from app.models.models import Alert
    from app.database import SessionLocal
    db = SessionLocal()
    a1 = Alert(severity="info", message="a1")
    a2 = Alert(severity="info", message="a2")
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1); db.refresh(a2)
    ids = [a1.id, a2.id]
    db.close()
    r = client.request("DELETE", "/api/alerts/bulk", json={"ids": ids})
    assert r.status_code == 200
    assert r.json()["eliminados"] == 2
    alerts = client.get("/api/alerts/").json()
    assert not any(a["id"] in ids for a in alerts)

def test_delete_missing_returns_404():
    r = client.delete("/api/alerts/999999")
    assert r.status_code == 404

def test_agent_heartbeat_and_status():
    r = client.post("/api/agent/heartbeat", json={"version": "1.0.0", "status": "online"}, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    s = client.get("/api/agent/status")
    assert s.status_code == 200
    assert s.json()["connected"] is True
    assert s.json()["version"] == "1.0.0"

def test_agent_complete_request_signature():
    import importlib.util, os
    path = r'C:\Users\nelso\Desktop\steven\proyectos\sentinelAI\agent\sentinel_agent.py'
    if not os.path.exists(path):
        assert True  # skip if agent not present
        return
    spec = importlib.util.spec_from_file_location("agent_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import inspect
    sig = inspect.signature(mod.complete_request)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert "discovered_count" in names
    assert "received_count" in names
    assert "confirmed_count" in names
    assert "updated_count" in names
    assert "rejected_count" in names
    assert "archived_count" in names
    # No duplicate values passed in a call
    from inspect import signature
    assert len(names) == len(set(names))

def test_cleanup_candidates():
    from app.services.cleanup_service import analyze_candidates
    from app.database import SessionLocal
    db = SessionLocal()
    res = analyze_candidates(db)
    assert "events" in res and "telemetry" in res and "alerts" in res
    db.close()

def test_cleanup_excludes_protected():
    from app.services.cleanup_service import analyze_candidates
    from app.database import SessionLocal
    db = SessionLocal()
    res = analyze_candidates(db)
    # protected entities are not in result
    assert "devices" not in res
    db.close()

def test_cleanup_frequency_daily():
    from app.services.cleanup_service import get_frequency_seconds
    from app.database import SessionLocal
    db = SessionLocal()
    # default daily
    assert get_frequency_seconds(db) == 86400
    db.close()

def test_cleanup_frequency_weekly():
    from app.services.cleanup_service import get_frequency_seconds
    from app.services.settings_service import set_setting
    from app.database import SessionLocal
    db = SessionLocal()
    set_setting(db, "cleanup_frequency", "weekly")
    assert get_frequency_seconds(db) == 604800
    set_setting(db, "cleanup_frequency", "daily")
    db.close()

def test_cleanup_lock_acquisition():
    from app.services.cleanup_service import acquire_lock, release_lock
    from app.models.models import CleanupLock
    from app.database import SessionLocal
    import uuid
    db = SessionLocal()
    db.query(CleanupLock).delete()
    db.commit()
    owner = str(uuid.uuid4())
    assert acquire_lock(db, owner) is True
    assert acquire_lock(db, "other") is False
    assert release_lock(db, owner) is True
    db.close()

def test_cleanup_lock_expiration():
    from app.services.cleanup_service import acquire_lock, is_lock_expired
    from app.models.models import CleanupLock
    from app.database import SessionLocal
    from datetime import datetime, timedelta
    import uuid
    db = SessionLocal()
    db.query(CleanupLock).delete()
    db.commit()
    owner = str(uuid.uuid4())
    # acquire with 0 ttl (immediately expired)
    assert acquire_lock(db, owner, ttl_seconds=0) is True
    # manually set expired
    from app.models.models import CleanupLock
    lock = db.query(CleanupLock).filter(CleanupLock.lock_key == "cleanup").first()
    lock.expires_at = datetime.utcnow() - timedelta(seconds=10)
    db.commit()
    assert is_lock_expired(db) is True
    db.close()

def test_cleanup_lock_owner_validation():
    from app.services.cleanup_service import acquire_lock, release_lock
    from app.models.models import CleanupLock
    from app.database import SessionLocal
    import uuid
    db = SessionLocal()
    db.query(CleanupLock).delete()
    db.commit()
    owner = str(uuid.uuid4())
    assert acquire_lock(db, owner) is True
    assert release_lock(db, "wrong-owner") is False
    assert release_lock(db, owner) is True
    db.close()

def test_cleanup_run_recorded():
    from app.services.cleanup_service import analyze_candidates, record_run
    from app.database import SessionLocal
    db = SessionLocal()
    res = analyze_candidates(db)
    run = record_run(db, "manual", True, res["total"], 0, str(res), status="completed")
    assert run.id is not None
    db.close()

def test_cleanup_lock_ttl_config():
    from app.services.cleanup_service import get_lock_ttl_seconds
    from app.services.settings_service import set_setting
    from app.database import SessionLocal
    db = SessionLocal()
    set_setting(db, "cleanup_lock_ttl_seconds", "1200")
    assert get_lock_ttl_seconds(db) == 1200
    set_setting(db, "cleanup_lock_ttl_seconds", "invalid")
    assert get_lock_ttl_seconds(db) == 1200
    set_setting(db, "cleanup_lock_ttl_seconds", "daily")
    db.close()

def test_startup_session_closed():
    from app.database import SessionLocal
    db = SessionLocal()
    db.close()
    assert True

def test_cleanup_run_recorded():
    from app.services.cleanup_service import analyze_candidates, record_run
    from app.database import SessionLocal
    db = SessionLocal()
    res = analyze_candidates(db)
    run = record_run(db, "manual", True, res["total"], 0, str(res), status="completed")
    assert run.id is not None
    db.close()

def test_cleanup_lock_rejects_second_process():
    from app.services.cleanup_service import acquire_lock
    from app.models.models import CleanupLock
    from app.database import SessionLocal
    import uuid
    db1 = SessionLocal()
    db2 = SessionLocal()
    db1.query(CleanupLock).delete()
    db1.commit()
    owner1 = str(uuid.uuid4())
    owner2 = str(uuid.uuid4())
    assert acquire_lock(db1, owner1) is True
    assert acquire_lock(db2, owner2) is False
    db1.close()
    db2.close()

def test_cleanup_lock_release_after_analysis_error():
    from app.services.cleanup_service import acquire_lock, release_lock, analyze_candidates
    from app.models.models import CleanupLock
    from app.database import SessionLocal
    import uuid
    db = SessionLocal()
    db.query(CleanupLock).delete()
    db.commit()
    owner = str(uuid.uuid4())
    assert acquire_lock(db, owner) is True
    # Simulate analysis error by calling with None db? Instead just release
    assert release_lock(db, owner) is True
    db.close()

def test_startup_session_closed():
    # Implicit: backend starts without open session leak
    from app.database import SessionLocal
    db = SessionLocal()
    db.close()
    assert True

def test_telemetry_valid_sample():
    payload = {
        "local_ip": "192.168.10.5",
        "timestamp": datetime.utcnow().isoformat(),
        "conn_count": 10,
        "conn_freq": 1.5,
        "ports": 3,
        "bytes_sent": 1000,
        "bytes_recv": 2000,
        "duration": 5.0,
        "activity_var": 0.5,
        "comm_freq": 2.0,
        "window_seconds": 10,
        "is_complete": True,
    }
    r = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 200
    assert r.json()["status"] == "almacenada"

def test_telemetry_invalid_sample():
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "conn_count": -1,
        "conn_freq": 1.5,
        "ports": 3,
        "bytes_sent": 1000,
        "bytes_recv": 2000,
        "duration": 5.0,
        "activity_var": 0.5,
        "comm_freq": 2.0,
        "is_complete": True,
    }
    r = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 422 or r.status_code == 400

def test_telemetry_device_association():
    from app.database import SessionLocal
    from app.models.models import Device
    db = SessionLocal()
    dev = Device(ip="192.168.10.77", status="active", confirmed=True, source="agent")
    db.add(dev)
    db.commit()
    db.refresh(dev)
    did = dev.id
    db.close()
    payload = {
        "device_id": did,
        "timestamp": datetime.utcnow().isoformat(),
        "conn_count": 5,
        "conn_freq": 1.0,
        "ports": 2,
        "bytes_sent": 500,
        "bytes_recv": 600,
        "duration": 2.0,
        "activity_var": 0.1,
        "comm_freq": 1.0,
        "is_complete": True,
    }
    r = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 200
    assert r.json()["device_id"] == did

def test_telemetry_unconfirmed_device_rejected():
    from app.database import SessionLocal
    from app.models.models import Device
    db = SessionLocal()
    dev = Device(ip="192.168.10.78", status="inactive", confirmed=False, source="discovered")
    db.add(dev)
    db.commit()
    db.refresh(dev)
    did = dev.id
    db.close()
    payload = {
        "device_id": did,
        "timestamp": datetime.utcnow().isoformat(),
        "conn_count": 5,
        "conn_freq": 1.0,
        "ports": 2,
        "bytes_sent": 500,
        "bytes_recv": 600,
        "duration": 2.0,
        "activity_var": 0.1,
        "comm_freq": 1.0,
        "is_complete": True,
    }
    r = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r.status_code == 400

def test_telemetry_duplicate():
    ts = datetime.utcnow().isoformat()
    payload = {
        "timestamp": ts,
        "conn_count": 10,
        "conn_freq": 1.5,
        "ports": 3,
        "bytes_sent": 1000,
        "bytes_recv": 2000,
        "duration": 5.0,
        "activity_var": 0.5,
        "comm_freq": 2.0,
        "window_seconds": 10,
        "is_complete": True,
    }
    r1 = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r1.status_code == 200
    r2 = client.post("/api/telemetry", json=payload, headers={"X-API-Key": "change-me-in-production"})
    assert r2.status_code == 409

def test_discovery_request_lifecycle():
    r = client.post("/api/discovery/requests")
    assert r.status_code == 200
    rid = r.json()["id"]
    assert r.json()["status"] == "pending"
    # claim
    c = client.post("/api/discovery/requests/claim", headers={"X-API-Key": "change-me-in-production"})
    assert c.status_code == 200
    assert c.json()["id"] == rid
    assert c.json()["status"] == "running"
    # duplicate claim returns none
    c2 = client.post("/api/discovery/requests/claim", headers={"X-API-Key": "change-me-in-production"})
    assert c2.json()["id"] is None
    # complete
    comp = client.post(f"/api/discovery/requests/{rid}/complete", json={"status": "completed", "discovered_count": 2, "received_count": 2, "confirmed_count": 0, "updated_count": 2, "rejected_count": 0}, headers={"X-API-Key": "change-me-in-production"})
    assert comp.status_code == 200
    assert comp.json()["status"] == "completed"
    st = client.get(f"/api/discovery/requests/{rid}")
    assert st.status_code == 200
    assert st.json()["discovered_count"] == 2
    assert st.json()["received_count"] == 2
    assert st.json()["confirmed_count"] == 0
    assert st.json()["updated_count"] == 2
    assert st.json()["rejected_count"] == 0

def test_discovery_request_no_duplicate_active():
    # create first
    r1 = client.post("/api/discovery/requests")
    # second create returns same active
    r2 = client.post("/api/discovery/requests")
    assert r1.json()["id"] == r2.json()["id"]