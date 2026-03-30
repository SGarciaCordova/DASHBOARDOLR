# 📜 Reglas del Agente — Antigravity SGC (v2.1)

## 🛠️ Antes de Operar
1. **Checkpoint Git**: `git add . && git commit -m "checkpoint: [tarea]"` (Obligatorio antes de cambios).
2. **Plan de Acción**: Mostrar lista de archivos a modificar y lógica técnica; esperar aprobación `OK`.
3. **Aislamiento**: Modificar solo un módulo/lógica a la vez.

## 🧹 Orden y Limpieza (Crítico)
1. **No Clutter**: NUNCA dejes archivos `test_*.py`, `check_*.py`, o imágenes/logs de debug en el root o carpetas de proyecto tras finalizar.
2. **Eliminación**: Si creas un script temporal, bórralo al terminar la tarea.
3. **Rutas**: Usa rutas absolutas o relativas al root siempre partiendo de la estructura estándar.

## 🛡️ Seguridad y Core
*   **Prohibido Tocar (sin permiso)**: `Dashboard.py`, `auth_system/models.py`, `auth_system/database.py`.
*   **Secretos**: No leas ni muestres contenido de `.env` o `credentials.json`.
*   **Base de Datos**: Preferir `SQLAlchemy` sobre SQL crudo. El sistema soporta Supabase (Cloud) y SQLite (Local).

## 🚀 Stack & Componentes
*   **IA**: Motor de insights en `src/ai_summarizer.py` (Groq/Llama 3.3).
*   **KPIs**: Lógica en `src/kpis/`, visualización en `projects/`.
*   **Auth**: JWT + Cookies (Perpetual Login). No modifiques la lógica de tokens sin validar ruteo.

---
*Si no estás seguro del impacto de un cambio en el Dashboard principal, PREGUNTA.*
