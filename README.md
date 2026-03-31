# — Control Tower by SGC 

> **Última actualización del README:** 2026-02-19

Plataforma interna de dashboards operativos desarrollada para **operadores logísticos 3PL**. Proporciona visibilidad **en tiempo real** de las operaciones de entrada (Inbound), salida (Outbound), ocupación de almacén y estado de pedidos, consolidando datos de **Google Sheets** y sistemas **WMS externos** (Gator WMS) mediante scrapers automatizados.

El sistema está diseñado para correr en la red local del operador y se accede a través del navegador. Incluye autenticación con JWT, sesiones persistentes vía cookies, y soporte para Docker.

---

##  Tabla de Contenidos

- [Stack Tecnológico](#-stack-tecnológico)
- [Arquitectura General](#-arquitectura-general)
- [Estructura de Carpetas](#-estructura-de-carpetas)
- [Módulos y Páginas](#-módulos-y-páginas)
- [Estado Actual de Desarrollo](#-estado-actual-de-desarrollo)
- [Convenciones del Proyecto](#-convenciones-del-proyecto)
- [Reglas para Agentes IA](#-reglas-para-agentes-ia)
- [Cómo Correr el Proyecto Localmente](#-cómo-correr-el-proyecto-localmente)
- [Variables de Entorno](#-variables-de-entorno)

---

## Stack Tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| **Framework UI** | Streamlit (Python) | Multi-page app via `st.navigation()` |
| **Frontend visual** | HTML/CSS/JS embebido vía `st.components.v1.html()` | Chart.js para gráficos. CSS custom por dashboard. |
| **Backend / Lógica** | Python 3.11 | Pandas, NumPy, SciPy, scikit-learn |
| **Base de datos auth** | SQLite (`auth_system/auth.db`) | SQLAlchemy ORM. Configurable a MySQL vía `DATABASE_URL` |
| **Base de datos WMS** | SQLite (`data/wms_data.db`) | Datos de scrapers Reebok (Inbound/Outbound/Airport) |
| **Base de datos sistema** | SQLite (`sgc_system.db`) | Cache local de datos de Google Sheets (OLR) |
| **Fuente de datos OLR** | Google Sheets API | `gspread` + `oauth2client`. Hoja: `REPORTE MR 2026 RICARDO` |
| **Fuente de datos Reebok** | Scrapers Selenium → WMS Gator | Chrome headless. `webdriver-manager` + `fake-useragent` |
| **Fuente de datos Ubicaciones** | CSV + Google Sheets | Inventarios en `data/inventarios/`, Maestros en Sheets |
| **Autenticación** | JWT + Cookies | `bcrypt` para hash, `PyJWT` para tokens, `extra-streamlit-components` para cookies |
| **Contenedorización** | Docker + Docker Compose | Base image: `selenium/standalone-chrome:latest` |
| **Zona horaria** | `America/Mexico_City` | Configurada en `.env` y `docker-compose.yml` |

### Dependencias clave (`requirements.txt`)

```
streamlit, pandas, numpy, gspread, oauth2client, matplotlib, plotly, scipy,
statsmodels, xlsxwriter, selenium, webdriver-manager, fake-useragent, openpyxl,
scikit-learn, cachetools, altair, requests, watchdog, urllib3, SQLAlchemy,
pymysql, bcrypt, python-dotenv, cryptography, extra-streamlit-components, pyjwt
```

---

##  Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                      NAVEGADOR (localhost:8501)                  │
│  ┌───────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │Dashboard  │  │Dashboard     │  │Airport   │  │Dashboard  │  │
│  │ON (OLR)   │  │Reebok        │  │Modes     │  │Ubicaciones│  │
│  └─────┬─────┘  └──────┬───────┘  └────┬─────┘  └─────┬─────┘  │
└────────┼────────────────┼───────────────┼──────────────┼────────┘
         │                │               │              │
┌────────▼────────────────▼───────────────▼──────────────▼────────┐
│                   Dashboard.py (Entry Point)                     │
│                   - Login con JWT/Cookie                         │
│                   - st.navigation() multi-page                   │
│                   - auth_system/* para sesiones                  │
└────────┬────────────────┬───────────────┬──────────────┬────────┘
         │                │               │              │
    ┌────▼─────┐   ┌──────▼──────┐  ┌─────▼─────┐ ┌─────▼────────┐
    │ src/     │   │ projects/   │  │ projects/ │ │ src/         │
    │data_loader│   │ Reebok/    │  │ OLR/      │ │ubicaciones_  │
    │kpi_engine│   │ wms_scraper│  │           │ │loader        │
    │alert_eng │   │ unificador │  │           │ │              │
    │ml_predict│   │ aeropuerto │  │           │ │              │
    └────┬─────┘   └──────┬──────┘  └─────┬─────┘ └─────┬────────┘
         │                │               │              │
    ┌────▼─────┐   ┌──────▼──────┐  ┌─────▼─────┐ ┌─────▼────────┐
    │Google    │   │data/        │  │sgc_system │ │data/         │
    │Sheets API│   │wms_data.db  │  │.db        │ │inventarios/  │
    └──────────┘   └─────────────┘  └───────────┘ └──────────────┘
```

### Capas principales

1. **Capa de Presentación** — HTML/CSS/JS embebido en cada página Streamlit. Cada proyecto tiene sus propios archivos de estilos y scripts en `assets/`.
2. **Capa de Lógica** — Módulos en `src/` calculan KPIs, alertas, predicciones ML. Los dashboards Reebok consultan SQLite directamente.
3. **Capa de Datos** — Google Sheets (OLR), SQLite (Reebok WMS), CSVs (Inventarios/Ubicaciones).
4. **Capa de Extracción** — Scrapers Selenium en `projects/Reebok/` que obtienen datos del WMS Gator y los consolidan en SQLite.
5. **Capa de Autenticación** — `auth_system/` con SQLAlchemy ORM, bcrypt, JWT. Cookies persistentes (30 días).

---

## 📁 Estructura de Carpetas

```
Antigravity SGC/
├── Dashboard.py                  # ENTRY POINT — Login + st.navigation()
├── Template_Dashboard.py         # Plantilla para nuevos dashboards
├── bot_launcher.py               # Scheduler (08:00, 13:00, 18:00) para scrapers
│
├── auth_system/                  # Sistema de autenticación
│   ├── __init__.py
│   ├── database.py               # Engine SQLAlchemy, SessionLocal, get_db()
│   ├── models.py                 # Modelo User (SQLAlchemy)
│   ├── auth.py                   # hash_password, verify_password, authenticate_user, register_user
│   ├── auth_utils.py             # JWT: create_access_token, decode_access_token
│   ├── create_admin.py           # Script para crear usuario admin
│   └── auth.db                   # Base de datos de usuarios (gitignored)
│
├── src/                          # Lógica compartida (usado por OLR + Ubicaciones)
│   ├── data_loader.py            # Conexión Google Sheets, limpieza de datos, mock data
│   ├── kpi_engine.py             # Facade (importa desde src/kpis/) para compatibilidad
│   ├── kpis/                     # Lógica de KPIs modularizada (Entradas, Surtidos, etc.)
│   │   ├── entradas.py           # KPIs de Inbound
│   │   ├── surtidos.py           # KPIs de Outbound
│   │   ├── comparativas.py       # Lógica WoW y comparativas
│   │   └── helpers.py            # Funciones auxiliares de cálculo
│   ├── alert_engine.py           # Motor de alertas (SLA risk, KPI changes, delayed orders)
│   ├── ml_predictor.py           # Predicción ML de SLA breach (RandomForest/Heuristic)
│   ├── database.py               # CRUD SQLite para sgc_system.db (cache de Sheets)
│   ├── db_sync.py                # Sincronización Google Sheets → sgc_system.db
│   ├── ubicaciones_loader.py     # Carga/KPIs/Charts para Dashboard de Ubicaciones
│   ├── debug_heatmap.py          # Utilidad de debug
│   └── debug_sheet.py            # Utilidad de debug
│
├── projects/                     # Dashboards por cliente/proyecto
│   ├── OLR/
│   │   ├── Dashboard_ON.py       # Dashboard operativo OLR (Google Sheets)
│   │   └── Airport_Mode.py       # Modo Aeropuerto OLR (panel en tiempo real)
│   │
│   ├── Reebok/
│   │   ├── Dashboard_Reebok.py   # Dashboard operativo Reebok (SQLite)
│   │   ├── Airport_Mode_Reebok.py# Modo Aeropuerto Reebok
│   │   ├── wms_scraper.py        # Scraper principal: descarga Inbound/Outbound del WMS
│   │   ├── wms_scraper_embarcados.py # Scraper de órdenes finalizadas/embarcadas
│   │   ├── wms_aeropuerto_scraper.py # Scraper para datos de Airport Mode
│   │   ├── unificador.py         # Consolida CSVs descargados → SQLite (entradas/surtido)
│   │   ├── setup_aeropuerto_db.py# Crea tablas/vista para Airport Mode en wms_data.db
│   │   ├── wms_recorder.py       # Utilidad para grabar acciones WMS
│   │   └── downloads/            # CSVs descargados por scrapers (Inbound/Outbound)
│   │
│   └── Ubicaciones/
│       └── Dashboard_Ubicaciones.py # Dashboard de ocupación de almacén
│
├── assets/                       # Frontend assets (CSS/JS/imágenes)
│   ├── style.css                 # Estilos Dashboard ON (OLR)
│   ├── dashboard.js              # JS Dashboard ON (OLR) — ~35KB
│   ├── reebok_style.css          # Estilos Dashboard Reebok
│   ├── reebok_dashboard.js       # JS Dashboard Reebok
│   ├── reebok_airport_style.css  # Estilos Airport Mode Reebok
│   ├── reebok_airport_dashboard.js # JS Airport Mode Reebok
│   ├── ubicaciones_style.css     # Estilos Dashboard Ubicaciones
│   ├── ubicaciones_dashboard.js  # JS Dashboard Ubicaciones — ~32KB
│   ├── logo.png                  # Logo Antigravity
│   └── OLR-logistics-1024x870.png
│
├── data/                         # Datos persistentes
│   ├── wms_data.db               # SQLite con tablas Reebok (entradas, surtido, aeropuerto)
│   └── inventarios/              # CSVs de inventarios para Dashboard Ubicaciones
│       ├── on_inventory.csv
│       ├── reebok_inventory.csv
│       └── piarena_inventory.csv
│
├── .streamlit/config.toml        # Config Streamlit: address=0.0.0.0, port=8501
├── .env.example                  # Plantilla de variables de entorno
├── .env                          # Variables de entorno reales (gitignored)
├── credentials.json              # Google Sheets API credentials (gitignored)
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Build sobre selenium/standalone-chrome + Python 3.11
├── docker-compose.yml            # Servicio dashboard con volúmenes persistentes
├── entrypoint.sh                 # Init DBs + launch Streamlit (Docker)
├── .dockerignore
├── .gitignore
├── sgc_system.db                 # Cache local de Google Sheets (gitignored)
├── SECURITY_REVIEW.md            # Auditoría de seguridad del proyecto
├── Iniciar_Dashboard.bat/.ps1    # Scripts de arranque Windows
├── RUN_DASHBOARD.bat             # Script de arranque simplificado
└── setup_autostart.ps1           # Configuración de inicio automático Windows
```

---

## Módulos y Páginas

### Páginas del Dashboard (definidas en `Dashboard.py`)

| Sección | Página | Archivo | Fuente de datos |
|---|---|---|---|
| **On Cloud** | Dashboard ON | `projects/OLR/Dashboard_ON.py` | Google Sheets (`REPORTE MR 2026 RICARDO`) |
| **On Cloud** | Airport Mode ON | `projects/OLR/Airport_Mode.py` | Google Sheets (misma) |
| **Reebok** | Dashboard Reebok | `projects/Reebok/Dashboard_Reebok.py` | SQLite `data/wms_data.db` |
| **Reebok** | Airport Mode Reebok | `projects/Reebok/Airport_Mode_Reebok.py` | SQLite `data/wms_data.db` |
| **Ubicaciones** | Dashboard de Ubicaciones | `projects/Ubicaciones/Dashboard_Ubicaciones.py` | CSVs + Google Sheets |

### Scrapers Reebok

| Script | Función | Output |
|---|---|---|
| `wms_scraper.py` | Descarga reportes Inbound/Outbound del WMS Gator | CSVs en `projects/Reebok/downloads/` |
| `wms_scraper_embarcados.py` | Descarga órdenes finalizadas/embarcadas | CSVs en `projects/Reebok/downloads/` |
| `wms_aeropuerto_scraper.py` | Scraper para datos de Airport Mode | Directo a SQLite (`wms_aeropuerto_raw`, `inbound_scord_despachados_raw`) |
| `unificador.py` | Consolida CSVs descargados → SQLite | Tablas `entradas` y `surtido` en `wms_data.db` |
| `bot_launcher.py` | Ejecuta `wms_scraper.py` → `unificador.py` en horario (08:00, 13:00, 18:00) | Logs en `bot_launcher.log` |

### Bases de datos SQLite

| Archivo | Tablas principales | Usado por |
|---|---|---|
| `auth_system/auth.db` | `users` (SQLAlchemy) | Login/Auth |
| `data/wms_data.db` | `entradas`, `surtido`, `wms_aeropuerto_raw`, `inbound_scord_despachados_raw`, vista `wms_aeropuerto` | Dashboards Reebok |
| `sgc_system.db` | `entradas`, `surtidos`, `metadata` | Cache local de Google Sheets (OLR) |

---

##  Estado Actual de Desarrollo

### Terminado y Funcional

- **Sistema de autenticación** — Login con bcrypt, JWT, cookies persistentes (30 días), bloqueo por intentos fallidos
- **Dashboard ON (OLR)** — KPIs de Entradas/Surtidos, filtros por fecha, comparación WoW, gráficos interactivos con modales, exportación a Excel
- **Airport Mode ON** — Panel tipo aeropuerto para órdenes activas, estados (Demorado/Riesgo/A Tiempo/Listo), órdenes completadas
- **Motor de alertas** — Detección de riesgo SLA 72h, cambios en KPIs, órdenes vencidas
- **Dashboard Reebok** — Pipeline Inbound/Outbound, KPIs desde WMS, heatmap de ocupación, actualización automática
- **Airport Mode Reebok** — Panel de órdenes activas/despachadas desde WMS
- **Scrapers Reebok** — 3 scrapers con Selenium (inbound/outbound, embarcados, aeropuerto), con jitter anti-detección
- **Unificador de datos** — Consolida CSVs descargados en SQLite
- **Bot Launcher** — Scheduler automático 3x/día para scrapers
- **Dashboard de Ubicaciones** — Ocupación de almacén por cliente (ON, Reebok, Piarena), heatmap, top SKUs, distribución por nivel
- **Docker** — Contenerización completa con `selenium/standalone-chrome`, volúmenes para DBs
- **Template Dashboard** — Plantilla funcional para crear nuevos dashboards

### 🔧 En Desarrollo / Parcialmente Implementado

- **Predicción ML de SLA** — `src/ml_predictor.py` implementado con RandomForest + fallback heurístico,etiquetado como "En Mantenimiento" en la UI
- **Sincronización Sheets → SQLite** — `src/db_sync.py` implementado pero no integrado automáticamente en el flujo principal

### Pendiente / Sin Implementar

- **Panel de administración de usuarios** — No existe UI para gestionar usuarios; solo el script `create_admin.py`
- **Desbloqueo automático de cuentas** — Se bloquean a los 3 intentos fallidos pero no se desbloquean automáticamente
- **HTTPS / Proxy reverso** — El dashboard se sirve en HTTP plano
- **Tests automatizados** — No hay suite de tests
- **CI/CD** — No hay pipeline de integración continua
- **Logs centralizados** — Cada scraper tiene su propio archivo de log, no hay sistema unificado

---

## 📐 Convenciones del Proyecto

### Nombres de archivos

| Tipo | Convención | Ejemplo |
|---|---|---|
| Dashboard | `Dashboard_[Nombre].py` | `Dashboard_Reebok.py` |
| Airport Mode | `Airport_Mode_[Nombre].py` | `Airport_Mode_Reebok.py` |
| Scraper | `wms_[tipo]_scraper.py` | `wms_aeropuerto_scraper.py` |
| CSS | `[nombre]_style.css` | `reebok_style.css` |
| JS | `[nombre]_dashboard.js` | `reebok_dashboard.js` |
| Módulo src | `nombre_descripción.py` (snake_case) | `kpi_engine.py` |

### Estructura de un Dashboard

Cada página de dashboard sigue este patrón:

1. **Imports** — Streamlit + módulos de `src/`
2. **Carga de datos** — Con `@st.cache_data` o consultas SQLite directas
3. **Cálculo de KPIs** — Usando funciones de `src/kpi_engine.py` o inline
4. **Serialización** — Todos los datos se empaquetan en un dict JSON (`all_kpis` o `master_data`)
5. **Sanitización** — Función `sanitize()` convierte tipos NumPy a tipos Python nativos
6. **Carga de assets** — Lee `assets/*.css` y `assets/*.js` como strings
7. **Renderización** — HTML completo generado como f-string, inyectado con `st.components.v1.html()`

### Patrones de código

- **Frontend embebido** — No se usa Streamlit nativo para visualización; todo el UI se renderiza como componente HTML con CSS/JS custom.
- **Datos Python → JS** — Se serializan a JSON con `json.dumps()` y se inyectan en una variable `const DATA = {...}` dentro del `<script>`.
- **Chart.js** — Se carga desde CDN (`cdn.jsdelivr.net`) para todos los gráficos.
- **Fuente tipográfica** — Inter (Google Fonts), sistema de variables CSS con `:root`.
- **Modales interactivos** — Overlay JS custom para drill-down en KPIs sin recargar la página.
- **Selenium scrapers** — Patrón: `setup_driver()` → `login()` → navegación → descarga → `wait_for_download()`. Incluyen `random_sleep()` para simular comportamiento humano.

### Idioma

- **Código**: Variable names, function names y comentarios técnicos en **inglés**.
- **UI/Strings visibles**: En **español** (labels, títulos, mensajes de error).
- **Nombres de tablas DB**: En **español** (`entradas`, `surtido`).

---

## 🤖 Reglas para Agentes IA

###  NO MODIFICAR (archivos críticos)

| Archivo | Razón |
|---|---|
| `Dashboard.py` | Entry point. Controla autenticación, routing y sesiones. Cambios aquí rompen toda la app. |
| `auth_system/database.py` | Motor de BD compartido. Si se modifica, todos los logins se rompen. |
| `auth_system/models.py` | Modelo ORM. Cambiar el schema sin migrar la DB borra los usuarios. |
| `auth_system/auth_utils.py` | Cambiar `SECRET_KEY` o `ALGORITHM` invalida todas las sesiones activas. |
| `.env` / `credentials.json` | Contienen secretos. **Nunca** leerlos, mostrarlos o modificarlos. |
| `docker-compose.yml` | Configuración de volúmenes y puertos. Cambiar rutas de volúmenes puede borrar datos. |
| `Dockerfile` | Cambiar la base image puede romper Chrome headless para los scrapers. |

###  MODIFICAR CON CUIDADO

| Archivo | Precaución |
|---|---|
| `src/kpis/` | Contiene TODA la lógica de KPIs de OLR modularizada. Cambiar una función aquí afecta múltiples dashboards. |
| `src/kpi_engine.py` | Facade para compatibilidad. No añadir lógica nueva aquí, usar `src/kpis/`. |
| `src/data_loader.py` | Cambiar la lógica de limpieza de fechas (`clean_date_series`) o de headers afecta tanto OLR como la sincronización. |
| `src/ubicaciones_loader.py` | El mapeo de clientes (`CLIENT_INVENTORY_MAP`) y sus IDs (`ON_CLIENT_IDS`, `REEBOK_CLIENT_ID`) son críticos. |
| `assets/*.js` | Los archivos JS son grandes (hasta 35KB) y contienen lógica de renderizado completa. Un error rompe todo el dashboard visual. |
| `assets/*.css` | Cambiar variables `:root` afecta colores globales del dashboard correspondiente. |
| `projects/Reebok/unificador.py` | Los mapeos de columnas CSV → DB deben coincidir con lo que produce el scraper. |

### SEGURO PARA MODIFICAR

| Archivo/Área | Notas |
|---|---|
| `projects/*/Dashboard_*.py` (UI sections) | Agregar secciones de UI o KPIs nuevos es seguro siempre que no se cambien los existentes. |
| `projects/*/Airport_Mode_*.py` | Páginas auto-contenidas. |
| `Template_Dashboard.py` | Es una plantilla; no se usa en producción. |
| `README.md`, `SECURITY_REVIEW.md` | Documentación. |
| `data/inventarios/*.csv` | Se pueden reemplazar/agregar CSVs de inventario. |
| Nuevos archivos en `src/` | Se pueden crear nuevos módulos sin afectar los existentes. |

### Procedimiento seguro para cambios

1. **Antes de editar un archivo `src/*.py`**: Buscar todos los archivos que lo importan con `grep -r "from src import" --include="*.py"` y `grep -r "import [module_name]" --include="*.py"`.
2. **Antes de editar estructura de DB**: Verificar el schema actual de las tablas en los archivos `setup_*.py` y `unificador.py`.
3. **Antes de editar CSS/JS**: Identificar cuál dashboard lo usa (el nombre del archivo lo indica: `reebok_style.css` → `Dashboard_Reebok.py`).
4. **Para agregar un nuevo cliente de Ubicaciones**: Editar `CLIENT_INVENTORY_MAP` en `src/ubicaciones_loader.py`, agregar el CSV a `data/inventarios/`, y agregar el filtro pill en `Dashboard_Ubicaciones.py`.
5. **Para agregar una nueva página**: Crear archivo `.py` en `projects/[Proyecto]/`, luego registrarlo en `Dashboard.py` dentro del dict `pages`.
6. **Nunca correr** `DROP TABLE` o `if_exists='replace'` sobre `auth.db` en producción — borra los usuarios.

---

##  Cómo Correr el Proyecto Localmente

### Pre-requisitos

- Python 3.11+
- Google Chrome (para scrapers Selenium)
- Archivo `credentials.json` de Google Sheets API (ver sección de Variables de Entorno)

### Opción 1: Ejecución directa (Desarrollo)

```powershell
# 1. Clonar el repositorio
cd C:\Users\TuUsuario\Desktop
git clone <url-del-repo> "Antigravity SGC"
cd "Antigravity SGC"

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
Copy-Item .env.example .env
# Editar .env con tus valores reales

# 5. Crear usuario admin
$env:ADMIN_PASSWORD = "tu_contraseña_segura"
python auth_system/create_admin.py

# 6. Ejecutar el dashboard
streamlit run Dashboard.py
# Acceder en http://localhost:8501
```

### Opción 2: Docker (Producción / Plug-and-Play)

```powershell
# 1. Configurar .env
Copy-Item .env.example .env
# Editar .env con tus valores

# 2. Build y arranque
docker compose up --build -d

# 3. Acceder
# http://localhost:8501

# 4. Ver logs
docker compose logs -f dashboard
```

> **Nota Docker:** Los volúmenes `./auth_system` y `./data` se montan para persistir las bases de datos fuera del contenedor. `shm_size: 2gb` es necesario para Chrome headless.

### Opción 3: Script de arranque Windows

Ejecutar `Iniciar_Dashboard.bat` o `RUN_DASHBOARD.bat` desde el explorador de archivos.

### Ejecutar scrapers manualmente

```powershell
# Scraper principal (Inbound + Outbound)
python projects/Reebok/wms_scraper.py

# Consolidar CSVs en SQLite
python projects/Reebok/unificador.py

# Scraper de embarcados
python projects/Reebok/wms_scraper_embarcados.py

# Scraper de Airport Mode
python projects/Reebok/wms_aeropuerto_scraper.py

# Ejecutar el scheduler automático (loop infinito)
python bot_launcher.py
```

---

##  Variables de Entorno

Copiar `.env.example` a `.env` antes de ejecutar. Variables requeridas:

| Variable | Requerida | Descripción |
|---|---|---|
| `DATABASE_URL` | No | URL de la BD de auth. Default: `sqlite:///./auth_system/auth.db` |
| `JWT_SECRET_KEY` | **Sí** | Clave secreta para firmar tokens JWT. Generar una clave aleatoria larga. |
| `ADMIN_EMAIL` | No | Email del admin al crear con `create_admin.py`. Default: `admin` |
| `ADMIN_PASSWORD` | Solo para `create_admin.py` | Contraseña del admin. |
| `WMS_URL` | No | URL del WMS Gator. Default: `https://apolo.soft-gator.com/gatorwolr/index.jsp` |
| `WMS_USER` | **Sí** (para scrapers) | Usuario del WMS |
| `WMS_PASS` | **Sí** (para scrapers) | Contraseña del WMS |
| `DOCKER_ENV` | No | `1` para Docker (activa Chrome headless). `0` o vacío para local. |
| `TZ` | No | Zona horaria. Default: `America/Mexico_City` |

Adicionalmente se necesita `credentials.json` (Google Sheets API service account key) en la raíz del proyecto para los dashboards OLR y Ubicaciones.

---

*Documentación generada desde el análisis directo del código fuente del repositorio.*
