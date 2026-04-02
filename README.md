# 🌌 Antigravity SGC — El Ecosistema Logístico Inteligente

> **Versión:** 3.0 (Edición 2026) | **Status:** 🟢 Operativo & Productivo | **Tecnología:** Full-Stack Python + Supabase + IA.

---

## 💎 ¿Qué es Antigravity SGC?

**Antigravity SGC** no es solo un tablero de datos; es una **central de mando inteligente** diseñada para operadores logísticos (3PL) que buscan trascender los límites convencionales de gestión. 

Este ecosistema integra datos en tiempo real de múltiples fuentes (WMS Gator, SCORD, Google Sheets) para ofrecer visibilidad absoluta, alertas predictivas mediante Machine Learning y una interfaz de usuario de alto rendimiento (High-Density Dark Mode).

## 🏗️ Ingeniería de Datos & Flujo Operativo

El sistema opera bajo un arquitectura **ETL (Extract, Transform, Load)** de alta disponibilidad:

1.  **🤖 Ingesta Robótica (Selenium/Automated Bots):** 
    Utilizamos bots programados en Python con **Selenium (Chromium)** que acceden a portales WMS.
     Estos simulan la navegación humana, descargan reportes crudos y los procesan en memoria antes de cualquier inserción.
2.  **🧠 Capa de Datos (Supabase / PostgresSQL):** 
    A diferencia de un archivo local, usamos **Supabase** como DB relacional centralizada. Esto permite que varios usuarios consulten el dashboard simultáneamente con datos consistentes y persistencia de auditoría.
3.  **👁️ Presentación & Reactividad (Streamlit):** 
    El frontend está construido sobre **Streamlit**, inyectando componentes avanzados de **JavaScript (Chart.js)** y CSS personalizado para una experiencia de usuario (UX) fluida y reactiva.
4.  **🔮 Motor Predictivo (Machine Learning):** 
    Implementamos lógica de **Random Forest** y heurísticas temporales para calcular el "Ritmo de Salida vs Meta". El sistema proyecta la hora de finalización basada en el rendimiento histórico y actual de la operación.

---

## 🚀 Módulos Críticos

### 📦 Dashboard OLR (Dashboard ON)
Optimizado para el monitoreo de **Logística de Salida**.
- **Fulfillment & SLA Tracking:** Cálculo granular de tiempos de respuesta por pedido.
- **Alert Engine:** Sistema de notificaciones que detecta 'cuellos de botella' antes de que el SLA se vea comprometido.
- **Smart Data Cleansing:** Limpieza automática de NaN y errores de origen (Google Sheets) mediante **Pandas**.

### 👟 Reebok (Airport Mode)
Diseñado para la alta densidad visual en **Centro de Distribución**.
- **Sincronización Automática:** Procesa datos de `inbound_scord_despachados_raw` para generar reportes dinámicos.
- **Live Feed:** Actualización sin parpadeo de pantalla (Zero-Flicker) para pantallas industriales.

### 🧱 Gestión de Ubicaciones
- **Spatial Analytics:** Análisis de densidad de almacenamiento por pasillo.
- **Heatmaps Logísticos:** Visualización de la 'temperatura' de inventario para optimizar el picking.

### 🔐 Seguridad & Control de Acceso (RBAC)
- **Autenticación Robusta:** Implementamos **Hasheo BCrypt** para contraseñas y **JWT (JSON Web Tokens)** para sesiones persistentes seguras en cookies.
- **Roles Diferenciados:** Acceso granular (Admin, Gerencia, MD Senior) que filtra la visibilidad de datos sensibles según el perfil.
- **Auditoría de Sesiones:** Registro de ingresos y bloqueos automáticos tras múltiples intentos fallidos.

---

## 🛠️ Stack Tecnológico (Para los Curiosos)

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Interfaz** | Streamlit + Custom CSS/JS | Dashboard interactivo y ultra-rápido. |
| **Base de Datos** | Supabase (PostgreSQL) | Memoria central y persistencia global. |
| **Automatización** | Selenium (Python) | Extracción de datos de portales WMS. |
| **Inteligencia** | Groq (Llama 3.3) | Resúmenes ejecutivos generados por IA. |
| **Seguridad** | JWT & BCrypt | Acceso protegido por roles y sesiones persistentes. |
| **Networking** | Cloudflare Tunnels | Acceso seguro desde cualquier red externa. |

---

## 📂 Arquitectura del Proyecto

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

## 📌 Reglas de Oro del Proyecto

-   **Estética Premium:** La interfaz DEBE seguir el estándar Dark Mode con acentos vibrantes (neones sutiles, glassmorphism) para facilitar la lectura en entornos de baja luz.
-   **Calidad de Datos:** Ningún dato se muestra sin ser validado; si el WMS falla, el sistema alerta, no muestra errores.
-   **Seguridad:** Toda acción crítica queda registrada. El acceso está blindado por roles (Senior MDC, Ops Manager, Gerencia).

---

## 🏁 ¿Cómo encender el sistema?

Para usuarios finales, el proceso es tan simple como hacer doble clic:

1.  **💻 Desarrollo Local:** Ejecuta `RUN_LOCAL.bat`.
2.  **🌐 Acceso Externo:** Ejecuta `INICIAR_TUNEL.bat` para que el dashboard sea accesible fuera de la oficina.
3.  **⚙️ Producción:** Los archivos `docker-compose.yml` gestionan el despliegue a gran escala.

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

- **Predicción ML de SLA** — `src/ml_predictor.py` implementado con RandomForest + fallback heurístico, etiquetado como "En Mantenimiento" en la UI
- **Sincronización Sheets → SQLite** — `src/db_sync.py` implementado pero no integrado automáticamente en el flujo principal

### Pendiente / Sin Implementar

- **Panel de administración de usuarios** — No existe UI para gestionar usuarios; solo el script `create_admin.py`
- **Desbloqueo automático de cuentas** — Se bloquean a los 3 intentos fallidos pero no se desbloquean automáticamente
- **HTTPS / Proxy reverso** — El dashboard se sirve en HTTP plano
- **Tests automatizados** — No hay suite de tests
- **CI/CD** — No hay pipeline de integración continua
- **Logs centralizados** — Cada scraper tiene su propio archivo de log, no hay sistema unificado

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

---

> *"Llevando la logística más allá de la gravedad."*  
> **Antigravity SGC Team 2026**
