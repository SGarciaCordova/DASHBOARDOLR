# 🛡️ Seguridad — Antigravity SGC (Revision v2.1)

## ✅ Hallazgos Corregidos
1.  **JWT & Sessions**: Implementado flujo de tokens JWT con cookies seguras en `Dashboard.py`.
2.  **Bloqueo Automático**: Añadido `locked_until` (5 min) para recuperación autónoma.
3.  **Gestión de Secretos**: Archivo `credentials.json.json` eliminado; `.env` centraliza sensibles.
4.  **Base de Datos**: Soporte para Supabase (Cloud) configurado; paths dinámicos en producción.

## ⚠️ Pendientes / Monitoreo
1.  **Hardcoded WMS Creds**: Validar si `wms_scraper.py` ya lee de `.env`.
2.  **Admin Initial Pass**: Se recomienda rotar la clave inicial generada por scripts de setup.
3.  **Nginx Proxy**: Asegurar que en producción el tráfico pase por puerto 8080 (HTTPS/Proxy) y no por 8501 directamente.

## 📜 Recomendaciones Core
- **No commit de DBs**: `.db` en root debe estar ignorado.
- **API Keys**: Siempre en variables de entorno (Groq, Supabase, Google).
- **Update Dependencies**: Mantener `requirements.txt` limpio.

---
*Revisión realizada: 2026-03-17*s, código de autenticación, HTML estático y bases de datos.*
