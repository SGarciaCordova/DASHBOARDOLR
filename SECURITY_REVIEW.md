# Revisión de seguridad – Antigravity SGC

Resumen de hallazgos considerando **todas las variables** y archivos sensibles del proyecto.

---

## Crítico

### 1. Credenciales en código (create_admin.py)
- **Archivo:** `auth_system/create_admin.py`
- **Problema:** Contraseña de admin en texto plano: `password = "153138107<3<3"`.
- **Riesgo:** Cualquiera con acceso al repo puede acceder como administrador.
- **Acción:** Usar variable de entorno (ej. `ADMIN_PASSWORD`) o solicitar por stdin al ejecutar el script.

### 2. Credenciales WMS en scraper (wms_scraper.py)
- **Archivo:** `projects/Reebok/wms_scraper.py`
- **Problema:** `USER = "scordova"` y `PASS = "scordova123"` hardcodeados.
- **Riesgo:** Exposición de credenciales del WMS; reutilización en otros entornos.
- **Acción:** Leer usuario y contraseña desde variables de entorno (ej. `WMS_USER`, `WMS_PASS`) o desde un archivo de configuración no versionado.

### 3. Credenciales y salt en HTML (login_page.html)
- **Archivo:** `login_page.html`
- **Problemas:**
  - Salt en JavaScript: `var salt="3f42a4ad-d85f-45bf-be41-e0b3cd62699e";` (visible en el cliente).
  - Valores en inputs ocultos: `name="a" value="gatorapps"` y `name="b" value="phei1EongaequeeThoofohl1ooYee7Ik"` (posible token/secret).
- **Riesgo:** Si este HTML se sirve o se sube a un repo, el salt y el valor de `b` quedan expuestos; podrían usarse para suplantar o atacar el sistema Gator.
- **Acción:** No poner salts ni secrets en el front; si este HTML es una copia local del WMS externo, tratarlo como sensible y no versionarlo, o reemplazar valores por placeholders y documentar que se rellenan en despliegue.

---

## Alto

### 4. Archivo credentials.json
- **Estado:** Está en `.gitignore` (bien), pero existe `credentials.json.json` en el listado del proyecto.
- **Riesgo:** Si `credentials.json.json` contiene OAuth/Google y se sube al repo, hay fuga de credenciales.
- **Acción:** Añadir `credentials.json.json` y `**/credentials*.json` al `.gitignore`. No commitear ningún archivo de credenciales.

### 5. Base de datos por defecto (auth_system/database.py)
- **Archivo:** `auth_system/database.py`
- **Comportamiento:** Si no hay `DATABASE_URL` en `.env`, usa `sqlite:///./auth_system/auth.db`.
- **Riesgo:** En producción, si no se configura `.env`, se usa SQLite por defecto; además, la ruta es relativa y puede no ser la deseada.
- **Acción:** En producción, exigir `DATABASE_URL` (fallar si no existe) y no usar path por defecto con datos reales.

### 6. Falta de .env en el proyecto
- **Estado:** Existe `.env.example` con ejemplos; no hay `.env` en el repo (correcto).
- **Riesgo:** Si alguien despliega sin crear `.env`, la app puede usar valores por defecto o fallar de forma poco clara.
- **Acción:** Documentar en README que es obligatorio copiar `.env.example` a `.env` y rellenar variables; opcionalmente validar al arranque que las variables críticas existan.

---

## Medio

### 7. Sesión Streamlit (Dashboard.py)
- **Archivo:** `Dashboard.py`
- **Estado:** La “sesión” es `st.session_state.user`; no hay tokens JWT ni cookies firmadas.
- **Riesgo:** En Streamlit la sesión está ligada al servidor; si el servidor no está protegido (HTTPS, red interna, etc.), puede haber interceptación.
- **Acción:** Servir el dashboard solo por HTTPS y en red controlada; no exponer el puerto a internet sin autenticación inversa (ej. proxy con login).

### 8. Bloqueo por intentos fallidos (auth_system/auth.py)
- **Estado:** Tras 3 intentos fallidos se pone `account_locked = True`.
- **Riesgo:** No hay desbloqueo automático por tiempo ni mensaje claro al usuario; un admin debe desbloquear manualmente.
- **Acción:** Añadir desbloqueo tras X minutos o una cola de desbloqueo, y documentar cómo desbloquear (script o panel admin).

### 9. Base de datos sgc_system.db
- **Archivo:** `sgc_system.db` en la raíz.
- **Riesgo:** Si contiene datos de negocio o usuarios, no debería estar en el control de versiones.
- **Acción:** Añadir `*.db` o al menos `sgc_system.db` al `.gitignore` si no debe versionarse.

---

## Buenas prácticas ya presentes

- **Contraseñas de usuarios:** Hasheo con bcrypt en `auth_system/auth.py`.
- **DATABASE_URL:** Leída desde entorno en `auth_system/database.py`.
- **.gitignore:** Incluye `credentials.json`, `venv/`, `.env`.
- **SQL:** Uso de SQLAlchemy ORM (menor riesgo de inyección SQL si no se usa SQL crudo con concatenación).

---

## Resumen de acciones recomendadas

| Prioridad | Acción |
|-----------|--------|
| Crítica   | Quitar contraseña y usuario/contraseña WMS del código; usar variables de entorno o config no versionada. |
| Crítica   | Eliminar o no versionar `login_page.html` con salt y valor `b`; si se usa, reemplazar por placeholders. |
| Alta      | Añadir `credentials.json.json` y patrones de credenciales al `.gitignore`. |
| Alta      | En producción, exigir `DATABASE_URL` y no depender del default. |
| Media     | Añadir `*.db` o `sgc_system.db` al `.gitignore` si aplica. |
| Media     | Documentar creación de `.env` y, si se desea, validar variables al inicio. |

---

*Revisión realizada considerando variables de entorno, archivos de credenciales, código de autenticación, HTML estático y bases de datos.*
