import streamlit as st
import pandas as pd
from auth_system.database import engine, get_db
from sqlalchemy import text
from src.database import log_activity

# st.set_page_config(page_title="Gestión de Usuarios", page_icon="👤", layout="wide")

st.title("🛡️ Panel de Control de Usuarios")
st.markdown("---")

# Solo permitir acceso si es el admin supremo
if st.session_state.get("user", {}).get("email") != "admin":
    st.error("No tienes permisos suficientes para acceder a esta sección.")
    st.stop()

# --- LISTA DE USUARIOS ---
st.subheader("Usuarios Registrados")

with engine.connect() as conn:
    query = text("SELECT id, email, role, created_at, last_login, failed_attempts, account_locked FROM users ORDER BY id ASC")
    df = pd.read_sql(query, conn)

if not df.empty:
    # Formatear el dataframe para que sea más legible
    df['account_locked'] = df['account_locked'].apply(lambda x: "🔒 Bloqueado" if x else "✅ Activo")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No se encontraron usuarios registrados.")

# --- ACCIONES ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Desbloquear Usuario")
    email_to_unlock = st.text_input("Email del usuario a desbloquear")
    if st.button("Desbloquear"):
        if email_to_unlock:
            with engine.connect() as conn:
                try:
                    conn.execute(text("UPDATE users SET account_locked = FALSE, failed_attempts = 0 WHERE email = :email"), {"email": email_to_unlock})
                    conn.commit()
                    log_activity(st.session_state.user['email'], "PERMISSION_CHANGE", f"Usuario {email_to_unlock} desbloqueado")
                    st.success(f"Usuario {email_to_unlock} desbloqueado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Ingresa un email válido.")

with col2:
    st.subheader("Cambiar Rol")
    email_to_role = st.text_input("Email del usuario")
    new_role = st.selectbox("Nuevo Rol", ["admin", "gerencia", "moderador_reebok", "moderador_on"])
    if st.button("Actualizar Rol"):
        if email_to_role:
            if email_to_role == "admin":
                st.error("No puedes cambiar el rol del Admin Supremo.")
            else:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("UPDATE users SET role = :role WHERE email = :email"), {"role": new_role, "email": email_to_role})
                        conn.commit()
                        log_activity(st.session_state.user['email'], "PERMISSION_CHANGE", f"Rol de {email_to_role} cambiado a {new_role}")
                        st.success(f"Rol de {email_to_role} actualizado a {new_role}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning("Ingresa un email válido.")
