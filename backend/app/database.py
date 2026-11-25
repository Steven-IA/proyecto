from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import text

def _migrate_confirmed_column():
    try:
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(devices)")).fetchall()]
            if "confirmed" not in cols:
                conn.execute(text("ALTER TABLE devices ADD COLUMN confirmed BOOLEAN DEFAULT 0"))
                conn.commit()
    except Exception:
        pass

def _migrate_device_name_column():
    """Migración idempotente: añade devices.name si no existe."""
    try:
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(devices)")).fetchall()]
            if cols and "name" not in cols:
                conn.execute(text("ALTER TABLE devices ADD COLUMN name VARCHAR"))
                conn.commit()
    except Exception:
        pass

def _migrate_telemetry_identity():
    try:
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(network_telemetry)")).fetchall()]
            if not cols:
                return
            if "identity_key" not in cols:
                conn.execute(text("ALTER TABLE network_telemetry ADD COLUMN identity_key VARCHAR"))
                rows = conn.execute(text("SELECT id, device_id, local_ip FROM network_telemetry")).fetchall()
                for r in rows:
                    key = f"device:{r[1]}" if r[1] is not None else f"ip:{r[2] or 'unknown'}"
                    conn.execute(text("UPDATE network_telemetry SET identity_key=:k WHERE id=:i"), {"k": key, "i": r[0]})
                conn.commit()
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_network_telemetry_identity ON network_telemetry (identity_key, timestamp, window_seconds)"))
                conn.commit()
            except Exception:
                pass
    except Exception:
        pass

def _migrate_deleted_at():
    try:
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(devices)")).fetchall()]
            if "deleted_at" not in cols:
                conn.execute(text("ALTER TABLE devices ADD COLUMN deleted_at DATETIME"))
                conn.commit()
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_deleted_at ON devices (deleted_at)"))
                conn.commit()
            except Exception:
                pass
    except Exception:
        pass

def _migrate_discovery_request_counts():
    try:
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(discovery_requests)")).fetchall()]
            if not cols:
                return
            for col in ("received_count", "confirmed_count", "updated_count", "archived_count"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE discovery_requests ADD COLUMN {col} INTEGER DEFAULT 0"))
            conn.commit()
    except Exception:
        pass

def _ensure_settings_defaults():
    try:
        from .models.models import AppSetting
        from sqlalchemy.orm import Session
        db = Session(bind=engine)
        defaults = {
            "cleanup_enabled": "false",
            "cleanup_frequency": "daily",
            "retention_events_days": "30",
            "retention_telemetry_days": "7",
            "retention_alerts_days": "90",
            "cleanup_max_records": "1000",
            "cleanup_last_run": "",
            "cleanup_lock_ttl_seconds": "1200",
        }
        for k, v in defaults.items():
            existing = db.query(AppSetting).filter(AppSetting.key == k).first()
            if not existing:
                db.add(AppSetting(key=k, value=v))
        db.commit()
        db.close()
    except Exception:
        pass

def init_db():
    from . import models  # noqa
    Base.metadata.create_all(bind=engine)
    _migrate_confirmed_column()
    _migrate_device_name_column()
    _migrate_telemetry_identity()
    _migrate_deleted_at()
    _migrate_discovery_request_counts()
    _ensure_settings_defaults()