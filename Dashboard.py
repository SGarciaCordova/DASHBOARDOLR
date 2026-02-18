import streamlit as st
import extra_streamlit_components as stx
import time
from datetime import datetime, timedelta
from auth_system.database import engine, Base, get_db, get_config_warnings
from auth_system.models import User
from auth_system.auth import authenticate_user
from auth_system.auth_utils import create_access_token, decode_access_token, COOKIE_NAME, ACCESS_TOKEN_EXPIRE_DAYS

# 1. Configuración de página
# st.set_page_config debe ser el primer comando de Streamlit
st.set_page_config(page_title="Operacion OLR", page_icon="📦", layout="wide")

# 2. Inicializar base de datos
Base.metadata.create_all(bind=engine)

# 2.1 Validación de configuración al arranque (solo una vez por sesión)
if "config_warnings" not in st.session_state:
    st.session_state.config_warnings = get_config_warnings()

# 3. Gestión de sesión
if "user" not in st.session_state:
    st.session_state.user = None

# Inicializar Cookie Manager
cookie_manager = stx.CookieManager(key="auth_cookie_handler")

# Intentar recuperación por cookie (Perpetual Login)
if not st.session_state.user:
    # Intenta obtener el token de la cookie
    # Si acabamos de hacer logout, ignoramos la cookie (para evitar race condition)
    if st.session_state.get("logout_pending", False):
        st.session_state.logout_pending = False
    else:
        cookie_token = cookie_manager.get(COOKIE_NAME)
        
        if cookie_token:
            user_data = decode_access_token(cookie_token)
            if user_data:
                st.session_state.user = {
                    "email": user_data["sub"],
                    "role": user_data["role"]
                }

def login():
    st.title("Bienvenido a Antigravity SGC")
    st.write("Por favor, inicie sesión para continuar.")
    
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        with st.form("login_form"):
            email = st.text_input("Usuario / Email")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                db = next(get_db())
                user = authenticate_user(db, email, password)
                if user:
                    # Crear Token y guardar en Cookie
                    access_token = create_access_token(
                        data={"sub": user.email, "role": user.role},
                        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
                    )
                    cookie_manager.set(COOKIE_NAME, access_token, expires_at=datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))

                    st.session_state.user = {
                        "email": user.email,
                        "role": user.role
                    }
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")

    
def logout():
    # Set logout flag to prevent immediate re-login from cookie
    st.session_state.logout_pending = True
    
    # 1. Clear all other session state keys
    for key in list(st.session_state.keys()):
        if key != "logout_pending":
            del st.session_state[key]
            
    # 2. Invalidate/Overwrite session cookie
    if cookie_manager:
        cookie_manager.set(COOKIE_NAME, "", expires_at=datetime.now() - timedelta(days=1))
        # Note: cookie_manager.delete(COOKIE_NAME) is often redundant if we set expiration, 
        # but keeping it doesn't hurt. However, removing the sleep to be "immediate".
        cookie_manager.delete(COOKIE_NAME)
    
    # 3. Rerun immediately
    st.rerun()

# 4. Control de flujo principal
if not st.session_state.user:
    if st.session_state.config_warnings:
        with st.expander("⚠️ Avisos de configuración", expanded=True):
            for w in st.session_state.config_warnings:
                st.warning(w)
    login()
else:
    # Sidebar con información de usuario y botón de salir
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['email']}**")
        if st.button("Cerrar Sesión", type="primary"):
            logout()
        if st.session_state.config_warnings:
            with st.expander("⚠️ Avisos de configuración"):
                for w in st.session_state.config_warnings:
                    st.caption(w)
        st.divider()

    # Define pages
    pages = {
        "On Cloud": [
            st.Page("projects/OLR/Dashboard_ON.py", title="Dashboard ON", icon="👟", default=True),
            st.Page("projects/OLR/Airport_Mode.py", title="Airport Mode ON", icon="✈️"),
        ],
        "Reebok": [
            st.Page("projects/Reebok/Dashboard_Reebok.py", title="Dashboard Reebok", icon="👟"),
            st.Page("projects/Reebok/Airport_Mode_Reebok.py", title="Airport Mode Reebok", icon="✈️"),
        ],
        "Ubicaciones": [
            st.Page("projects/Ubicaciones/Dashboard_Ubicaciones.py", title="Dashboard de Ubicaciones", icon="📍"),
        ],
    }

    pg = st.navigation(pages)
    pg.run()
