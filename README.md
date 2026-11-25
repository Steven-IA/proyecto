# SentinelAI

Plataforma local de monitoreo y evaluación de ciberseguridad empresarial.

## Requisitos
- Docker Desktop (Windows 11)
- Python 3.11 (para desarrollo local)
- Node.js 20 (para desarrollo frontend)

## Ejecución con Docker
```powershell
copy .env.example .env
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f
```
Dashboard: http://localhost
API: http://localhost:8000/docs

Detener:
```powershell
docker compose down
```

## Desarrollo local
Backend:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```

## Modelos de IA
Entrenar explícitamente:
```powershell
python scripts/train_models.py
```
Los pesos se guardan en `models/`. No se reentrenan automáticamente al iniciar.

## Agente Windows
Ejecutar en el host para descubrir la red y enviar resultados al backend:
```powershell
python agent/sentinel_agent.py
```

Construir ejecutable:
```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --name sentinel_agent --distpath agent/dist --workpath agent/build agent/sentinel_agent.py
```

Ejecutar en segundo plano:
```powershell
$env:SENTINEL_API_URL="http://localhost:8000"
$env:AUTHORIZED_SUBNET="192.168.10.0/24"
$env:API_KEY="tu-api-key"
agent\dist\sentinel_agent.exe --daemon
```

Inicio automático en Windows (Programador de tareas):
```powershell
.\scripts\install_agent_task.ps1
```

Configuración segura de variables:
Crear `agent\.env.local` (no versionado) con:
```text
SENTINEL_API_URL=http://localhost:8000
AUTHORIZED_SUBNET=192.168.10.0/24
API_KEY=tu-api-key
```

## Portabilidad
Ver sección de pruebas en `openspec/changes/sentinelai-platform/tasks.md`. No se afirma compatibilidad universal sin pruebas.