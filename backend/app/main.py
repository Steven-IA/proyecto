import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, SessionLocal
from .services.cleanup_service import is_cleanup_enabled, analyze_candidates, record_run, acquire_lock, release_lock, get_frequency_seconds, get_lock_ttl_seconds
from .routers import (
    health_router, devices_router, discovery_router, availability_router,
    security_router, inference_router, vuln_router, alerts_router, reports_router, training_router,
    history_router, settings_router, discovery_requests_router, agent_router, ai_router, telemetry_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    startup_db = SessionLocal()
    try:
        enabled = is_cleanup_enabled(startup_db)
    finally:
        startup_db.close()
    task = None
    if enabled:
        async def scheduler():
            import uuid
            owner = str(uuid.uuid4())
            while True:
                interval = 86400
                lock_acquired = False
                db = None
                try:
                    db = SessionLocal()
                    interval = get_frequency_seconds(db)
                    # Wait before first execution
                    await asyncio.sleep(interval)
                    ttl = get_lock_ttl_seconds(db)
                    if not acquire_lock(db, owner, ttl_seconds=ttl):
                        # another process holds the lock
                        lock_acquired = False
                    else:
                        lock_acquired = True
                        try:
                            result = analyze_candidates(db)
                            record_run(db, "scheduled", True, result["total"], 0, str(result), status="completed")
                        except Exception as e:
                            try:
                                record_run(db, "scheduled", True, 0, 0, str(e), status="error", error=str(e))
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    try:
                        err_db = SessionLocal()
                        record_run(err_db, "scheduled", True, 0, 0, str(e), status="error", error=str(e))
                        err_db.close()
                    except Exception:
                        pass
                finally:
                    if db is not None:
                        if lock_acquired:
                            release_lock(db, owner)
                        db.close()
                # sleep until next interval
                await asyncio.sleep(interval)
        task = asyncio.create_task(scheduler())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="SentinelAI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

@app.get("/health")
def health_alias():
    return {"status": "ok", "mensaje": "SentinelAI operativo"}
app.include_router(devices_router)
app.include_router(discovery_router)
app.include_router(availability_router)
app.include_router(security_router)
app.include_router(inference_router)
app.include_router(vuln_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(training_router)
app.include_router(history_router)
app.include_router(settings_router)
app.include_router(discovery_requests_router)
app.include_router(agent_router)
app.include_router(ai_router)
app.include_router(telemetry_router)