# Reglas Permanentes para Agentes IA — Antigravity SGC

Lee este archivo completo antes de ejecutar cualquier tarea en este proyecto.

## Antes de cualquier cambio

1. SIEMPRE ejecutar git add . && git commit -m "checkpoint: antes de [descripción de la tarea]" sin esperar que el usuario lo pida
2. SIEMPRE mostrar un plan detallado de qué archivos vas a tocar y por qué, y esperar aprobación explícita antes de ejecutar
3. NUNCA modificar más de un módulo a la vez sin aprobación explícita

## Después de cualquier cambio

1. Listar todos los archivos modificados
2. Confirmar que los imports existentes no se rompieron
3. Preguntar si se debe hacer commit del resultado

## Archivos que NUNCA debes tocar sin permiso explícito

- Dashboard.py — entry point, rompe toda la app
- auth_system/database.py — motor de BD compartido
- auth_system/models.py — schema ORM, cambiar borra usuarios
- auth_system/auth_utils.py — invalida todas las sesiones activas
- .env y credentials.json — secretos, nunca leer ni mostrar
- docker-compose.yml — volúmenes de datos en producción
- assets/*.js — archivos grandes, un error rompe el dashboard visual

## Stack del proyecto

Python 3.11 + Streamlit + SQLite + Selenium + Docker. Ver README.md para contexto completo.
