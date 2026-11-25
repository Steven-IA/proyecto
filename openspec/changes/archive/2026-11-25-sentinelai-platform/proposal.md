# Proposal

## Why

Las pequeñas y medianas empresas necesitan una herramienta local, asequible y autocontenida para descubrir activos de red, evaluar su postura de seguridad y detectar anomalías mediante modelos de IA propios. Las soluciones existentes suelen depender de nube, agentes por host o infraestructura pesada. SentinelAI se ejecuta desde un único equipo Windows 11 (y mediante Docker Compose), manteniendo los datos en la red local y sin requerir servicios externos obligatorios.

## What Changes

- Nuevo backend FastAPI con persistencia SQLite, endpoints REST y WebSockets cuando sean necesarios.
- Dashboard React/Vite/Tailwind con nueve módulos reales conectados al backend.
- Motor de descubrimiento de red mediante ARP/ICMP/OUI, con Nmap opcional y solo en subred autorizada.
- Módulo de vulnerabilidades con consulta a NVD/OSV, caché local y tolerancia a fallos.
- Dos modelos PyTorch desarrollados y entrenados dentro del proyecto:
  - Network Transformer para detección de anomalías.
  - Security Classifier (MLP) para clasificación de riesgo.
- Despliegue mediante Docker Compose con persistencia de SQLite, pesos, datasets y reportes.
- Agente Windows ligero que descubre la red del host y envía resultados al backend mediante API autenticada.
- Generación de reportes PDF e historial de alertas.

### Restricciones transversales (obligatorias)

- Toda la interfaz, mensajes, alertas, formularios, reportes PDF y documentación README deben estar en español. Los nombres técnicos de clases, funciones, variables y archivos pueden permanecer en inglés.
- El frontend debe consumir endpoints reales del backend; no se permiten datos ficticios para aparentar funcionalidades terminadas.
- Los modelos PyTorch deben entrenarse realmente mediante scripts reproducibles, documentando origen de datasets, separación entrenamiento/validación/prueba, métricas y limitaciones. No se inventarán resultados ni se presentarán datos sintéticos como evidencia de detección real de amenazas.
- El agente Windows debe tener una prueba real de comunicación con el backend en Docker, descubrimiento de dispositivos y envío autenticado de resultados.
- Docker Compose debe garantizar persistencia de SQLite, pesos, datasets y reportes, con pruebas de reinicio y reconstrucción.
- Cada fase tendrá criterios de aceptación verificables, pruebas automatizadas y comprobaciones manuales cuando sean necesarias.
- La interfaz debe ser profesional, moderna y completa, con estados de carga, error y ausencia de datos en los nueve módulos.
- No se marcará ninguna tarea como completada únicamente por haber creado archivos; cada funcionalidad se implementará, ejecutará y verificará.

## Capabilities

### New Capabilities

- `device-discovery`: descubrimiento controlado de dispositivos en subred autorizada.
- `asset-inventory`: inventario persistente, consulta, filtrado, ordenamiento y detalle.
- `availability-monitoring`: comprobación de disponibilidad y historial.
- `security-assessment`: evaluación de condiciones de seguridad y entradas de riesgo.
- `network-anomaly-detection`: Transformer propio para anomalías de red con entrenamiento real.
- `security-risk-classification`: MLP propia para clasificación de riesgo con entrenamiento real.
- `vulnerability-management`: identificación de vulnerabilidades conocidas con caché y tolerancia a errores.
- `alert-management`: alertas ordenadas, persistencia y gestión.
- `reporting`: generación de reportes PDF en español.
- `platform-dashboard`: interfaz profesional en español con nueve módulos y estados reales.
- `backend-api`: API REST documentada y WebSockets cuando sea necesario.
- `data-persistence`: persistencia SQLite y gestión de datos.
- `containerized-deployment`: Docker Compose con persistencia, healthchecks y pruebas.
- `windows-discovery-agent`: agente Windows con comunicación autenticada y prueba real.

### Modified Capabilities

Ninguna (proyecto nuevo).

## Impact

- Nueva estructura de repositorio (backend, frontend, ai, agent, scripts).
- Nuevas dependencias: FastAPI, SQLAlchemy, Scapy, PyTorch, reportlab, etc.
- Requiere permisos de red en el host y manejo especial para Docker en Windows.
- Los modelos requieren tiempo de entrenamiento y almacenamiento persistente de pesos.
- Todas las superficies visibles al usuario y documentación deben estar en español.