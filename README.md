# Antigravity SGC — Sistema de Gestión y Control Logístico

**Versión:** 3.0 (Edición 2026) | **Status:** Operativo | **Tecnología:** Python, Supabase, Streamlit.

---

## Descripción del Proyecto

Antigravity SGC es una plataforma de monitoreo y control diseñada para operadores logísticos (3PL). El sistema integra datos en tiempo real de múltiples fuentes como WMS Gator, SCORD y Google Sheets, proporcionando visibilidad operativa, alertas preventivas y análisis de rendimiento mediante modelos de aprendizaje automático.

## Arquitectura y Flujo de Datos

El sistema implementa un ciclo ETL (Extract, Transform, Load) para garantizar la disponibilidad y consistencia de la información:

1.  **Ingesta de Datos (Selenium):** 
    Bots automatizados extraen reportes de portales WMS. Los datos se procesan en memoria para asegurar una limpieza efectiva antes de su almacenamiento.
2.  **Persistencia (Supabase / PostgreSQL):** 
    Uso de una base de datos relacional centralizada para permitir consultas concurrentes, trazabilidad de auditoría y persistencia de configuraciones.
3.  **Visualización (Streamlit):** 
    Interfaz desarrollada en Streamlit, complementada con componentes de JavaScript (Chart.js) y CSS personalizado para optimizar la representación de KPIs complejos.
4.  **Lógica Predictiva:** 
    Cálculo de ritmos operativos y proyecciones de cumplimiento de SLA basados en modelos estadísticos y heurísticas de rendimiento histórico.

---

## Módulos del Sistema

### Dashboard OLR (Salidas)
Monitoreo de indicadores de cumplimiento y niveles de servicio.
- **Seguimiento de SLA:** Cálculo por pedido y global.
- **Motor de Alertas:** Detección de desviaciones operativas y riesgos de incumplimiento.
- **Saneamiento de Datos:** Procesamiento automático de inconsistencias en orígenes externos.

### Reebok (Modo Aeropuerto)
Panel de visualización de alta densidad para centros de despacho.
- **Sincronización:** Actualización constante desde registros de SCORD.
- **Visualización Industrial:** Optimización para pantallas de gran formato con actualización de baja latencia.

### Gestión de Ubicaciones
- **Análisis Espacial:** Monitoreo de densidad de almacenamiento por pasillos y niveles.
- **Mapas Térmicos:** Identificación de áreas de alta rotación para optimización de picking.

### Seguridad y Control de Acceso (RBAC)
- **Autenticación:** Gestión de sesiones mediante JWT y almacenamiento seguro de credenciales con BCrypt.
- **Roles:** Acceso granular para perfiles Administrativos, Gerenciales y Operativos.
- **Auditoría:** Registro detallado de accesos y actividades críticas.

---

## Tecnologías Utilizadas

| Componente | Tecnología | Función |
| :--- | :--- | :--- |
| **Interfaz** | Streamlit, HTML/CSS/JS | Frontend y visualización de datos. |
| **Base de Datos** | Supabase (PostgreSQL) | Almacenamiento centralizado. |
| **Automatización** | Selenium (Python) | Extracción de datos de sistemas externos. |
| **Análisis** | Pandas, Scikit-learn | Procesamiento y modelos predictivos. |
| **Seguridad** | JWT, BCrypt | Autenticación y control de acceso. |
| **Infraestructura** | Docker, Cloudflare Tunnels | Despliegue y conectividad segura. |

---

## Estructura del Proyecto

```
Antigravity SGC/
├── Dashboard.py                  # Punto de entrada y gestión de navegación
├── Template_Dashboard.py         # Plantilla para nuevos módulos
├── bot_launcher.py               # Programador de tareas para scrapers
│
├── auth_system/                  # Módulos de autenticación y usuarios
│   ├── database.py               # Configuración de base de datos de usuarios
│   ├── models.py                 # Definición de modelos ORM
│   ├── auth.py                   # Lógica de autenticación y contraseñas
│   └── auth_utils.py             # Gestión de tokens JWT
│
├── src/                          # Librerías y lógica compartida
│   ├── data_loader.py            # Interfaces de carga y limpieza de datos
│   ├── kpi_engine.py             # Motor central de KPIs
│   ├── kpis/                     # Lógica modular de indicadores
│   ├── alert_engine.py           # Sistema de notificaciones operativas
│   ├── ml_predictor.py           # Modelos de predicción de SLA
│   ├── database.py               # Capa de datos para caché local
│   └── db_sync.py                # Sincronización entre fuentes externas y base de datos
│
├── projects/                     # Dashboards específicos por cliente
│   ├── OLR/                      # Dashboard y Modo Aeropuerto OLR
│   ├── Reebok/                   # Scrapers, unificadores y dashboards Reebok
│   └── Ubicaciones/              # Dashboard de ocupación de almacén
│
├── assets/                       # Recursos estáticos (CSS, JS, Imágenes)
├── data/                         # Bases de datos SQLite y archivos CSV persistentes
├── .streamlit/config.toml        # Configuración del servidor Streamlit
├── requirements.txt              # Dependencias del proyecto
├── Dockerfile                    # Configuración de contenedorización
└── docker-compose.yml            # Orquestación de servicios
```

---

## Lineamientos de Desarrollo

- **Consistencia Visual:** Las interfaces deben mantener el estándar de diseño establecido para asegurar la legibilidad en entornos industriales.
- **Validación de Datos:** No se debe presentar información sin una fase previa de normalización y limpieza.
- **Seguridad en Código:** Los secretos y claves de acceso deben gestionarse estrictamente a través de variables de entorno, nunca en el repositorio.

---

## Ejecución del Sistema

### Entorno Local
1. Instalar dependencias: `pip install -r requirements.txt`
2. Configurar variables de entorno en archivo `.env`.
3. Ejecutar: `streamlit run Dashboard.py`

### Entorno Docker
1. Construir y desplegar: `docker compose up --build -d`

---

## Notas para Agentes de Desarrollo

- **Archivos Críticos:** No modificar `Dashboard.py` ni módulos dentro de `auth_system/` sin una revisión exhaustiva de impacto en el sistema de navegación y seguridad.
- **Lógica de Negocio:** Las actualizaciones en `src/kpis/` afectan a múltiples componentes; verificar dependencias antes de aplicar cambios.

---

**Antigravity SGC Team 2026**
