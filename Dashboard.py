import streamlit as st
import extra_streamlit_components as stx
import time
from datetime import datetime, timedelta
import hashlib
import json
import os
from auth_system.database import engine, Base, get_db, get_config_warnings
from auth_system.models import User
from auth_system.auth import authenticate_user
from auth_system.auth_utils import create_access_token, decode_access_token, COOKIE_NAME, ACCESS_TOKEN_EXPIRE_DAYS
from src.database import log_activity

LOCKOUT_FILE = "lockout_registry.json"

def get_lockout_data():
    if os.path.exists(LOCKOUT_FILE):
        try:
            with open(LOCKOUT_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_lockout_data(data):
    with open(LOCKOUT_FILE, "w") as f:
        json.dump(data, f)

import base64

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def inject_login_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&family=Inter:wght@400;500;600;800&display=swap');

        /* Global background and font ONLY for Login */
        [data-testid="stAppViewContainer"], .stApp {
            background-color: #f0f2f5 !important;
            background-image: url("data:image/svg+xml,%3Csvg width='40' height='69.28203230275509' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M40 11.547L40 23.094L20 34.641L0 23.094L0 11.547L20 0L40 11.547ZM20 46.188L20 57.735L0 69.282L-20 57.735L-20 46.188L0 34.641L20 46.188ZM60 46.188L60 57.735L40 69.282L20 57.735L20 46.188L40 34.641L60 46.188Z' fill='none' stroke='%23e5e9f0' stroke-width='1'/%3E%3C/svg%3E") !important;
            font-family: 'Inter', sans-serif !important;
            color: #333333 !important;
        }

        /* Hide default Streamlit UI elements completely */
        [data-testid="stHeader"] {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stDeployButton {display: none !important;}
        
        /* Container styling */
        [data-testid="stForm"] {
            margin-top: -50px !important;
            background-color: #ffffff !important;
            border: 1px solid #ffffff !important;
            padding: 40px 40px 25px 40px !important;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.05), 0 3px 10px rgba(0, 0, 0, 0.03) !important;
            border-radius: 12px !important;
            position: relative;
        }
        
        h1 {
            color: #8b0000 !important;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0 0 2px 0 !important;
            padding: 0 !important;
            text-shadow: none !important;
        }

        .subtitle-container {
            display: flex;
            align-items: center;
        }

        .subtitle {
            color: #6c757d;
            font-size: 0.95rem;
            font-weight: 500;
        }

        .subtitle-line {
            flex-grow: 1;
            height: 1px;
            background-color: #ced4da;
            margin-left: 10px;
        }

        /* Status Indicator Row */
        .status-container {
            text-align: center;
            margin-bottom: 25px;
            font-size: 0.95rem;
        }
        .status-indicator {
            color: #2e8b57;
            font-weight: 600;
        }

        /* Text Input Fields */
        .stTextInput > div > div > input {
            background-color: #ffffff !important;
            color: #333333 !important;
            border: 1px solid #d1d5db !important;
            border-radius: 6px !important;
            padding: 12px 15px !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            text-align: center !important;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.02) !important;
            transition: all 0.2s ease;
        }
        .stTextInput > div > div > input::placeholder {
            color: #888888 !important;
            font-weight: 400 !important;
            text-align: center !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #15295c !important;
            box-shadow: 0 0 0 3px rgba(21, 41, 92, 0.1) !important;
            outline: none !important;
        }

        /* Hide labels */
        .stTextInput label {
            display: none !important;
        }

        /* Center the button container */
        [data-testid="stForm"] {
            text-align: center !important;
        }
        .stButton, [data-testid="stFormSubmitButton"] {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
            margin-top: 10px !important;
        }

        /* Login Button */
        [data-testid="stFormSubmitButton"] > button {
            width: 250px !important;
            margin: 0 auto !important;
            background-color: #15295c !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 25px !important;
            padding: 15px 30px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
        }
        [data-testid="stFormSubmitButton"] > button:hover {
            background-color: #0f1e40 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(21, 41, 92, 0.2) !important;
        }
        
        [data-testid="stFormSubmitButton"] > button:active {
            transform: scale(0.98);
        }

        /* Alerts and Errors Override */
        [data-testid="stAlert"] {
            border-radius: 6px !important;
            font-family: 'Inter', sans-serif !important;
            padding: 10px !important;
            margin-bottom: 10px !important;
        }
        
        /* Footer within card */
        .card-footer {
            text-align: center;
            margin-top: 40px; /* Lowered the entire footer section */
            color: #6c757d;
            font-size: 0.75rem;
            line-height: 1.4;
        }
        .designer-signature {
            font-family: 'Great Vibes', cursive;
            font-size: 1.2rem;
            font-weight: 500;
            color: #000000 !important;
            margin-top: 10px;
            letter-spacing: 0.5px;
            display: inline-block;
            opacity: 1;
        }
        </style>
    """, unsafe_allow_html=True)

# 1. Configuración de página
# st.set_page_config debe ser el primer comando de Streamlit
st.set_page_config(page_title="Operacion OLR", page_icon="📦", layout="wide")

# 2. Inicializar base de datos
@st.cache_resource(show_spinner=False)
def init_db():
    # Asegurar tablas en Supabase
    Base.metadata.create_all(bind=engine)
    return True
init_db()

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
                # LOG COOKIE LOGIN (Disabled per user request to avoid refresh spam)
                # log_activity(user_data["sub"], "LOGIN", "Inicio de sesión automático (Cookie)")

def login():
    inject_login_css()
    
    if 'session_hash' not in st.session_state:
        st.session_state.session_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16].upper()

    # Remove initial spacing to move card to the top
    st.write("", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            
            try:
                logo_b64 = get_base64_of_bin_file("assets/logo.png")
                img_tag = f'<img src="data:image/png;base64,{logo_b64}" width="100" style="object-fit: contain;" />'
            except Exception:
                # Fallback in case image is missing
                img_tag = '<div style="width: 100px; height: 100px; background: #ddd; border-radius: 50%;"></div>'

            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: flex-start; margin-bottom: 20px;">
                    <div style="margin-right: 15px; display: flex; align-items: center;">
                        {img_tag}
                    </div>
                    <div style="flex-grow: 1;">
                        <h1 style="text-align: left; margin-bottom: 0;">COMMAND CENTER</h1>
                        <div class="subtitle-container" style="justify-content: flex-start; margin-bottom: 0;">
                            <span class="subtitle">3PL Control Tower</span>
                            <div class="subtitle-line"></div>
                        </div>
                    </div>
                </div>
                
                <div class="status-container">
                    <span class="status-indicator">● System Operational</span>
                    <br>
                    <span style="font-size: 0.7rem; color: #6c757d;">
                        Database: {"☁️ Cloud (Supabase)" if "supabase" in engine.url.host else "🏠 Local (SQLite)"}
                    </span>
                </div>
            """, unsafe_allow_html=True)

            email = st.text_input("Email", label_visibility="collapsed", placeholder="ID de Operador / Email")
            password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Código de Autorización")
            
            alert_placeholder = st.empty()
            boot_placeholder = st.empty()
            
            # Custom Centered Button
            st.markdown("""
                <div style="display: flex; justify-content: center; margin-top: 15px;">
                    <style>
                        .stButton > button {
                            width: 280px !important;
                            background-color: #15295c !important;
                            color: white !important;
                            border-radius: 25px !important;
                            padding: 12px 30px !important;
                            border: none !important;
                            font-weight: 600 !important;
                        }
                    </style>
                </div>
            """, unsafe_allow_html=True)
            
            submit = st.form_submit_button("Acceder al Sistema", use_container_width=True)
            
            st.markdown(f'''
                <div class="card-footer">
                    v2.0 — Build 2026.01 | OLR Logistics | By SGC<br>
                    <div class="designer-signature">Designed by Sergio Cordova</div>
                </div>
            ''', unsafe_allow_html=True)
            
            if submit:
                username_key = email.strip()
                if not username_key:
                    alert_placeholder.error("ACCESS DENIED: Invalid Operator ID.")
                    st.stop()
                    
                lockout_data = get_lockout_data()
                user_lock = lockout_data.get(username_key, {"attempts": 0, "locked_until": None})
                
                is_locked = False
                if user_lock["locked_until"]:
                    locked_time = datetime.fromisoformat(user_lock["locked_until"])
                    if datetime.now() < locked_time:
                        is_locked = True
                        remaining_time = int((locked_time - datetime.now()).total_seconds())
                        alert_placeholder.error(f"SYSTEM LOCKOUT IN EFFECT. TERMINAL SECURED.\\nContact Supervisor. Retry available in {remaining_time} seconds.")
                    else:
                        user_lock["attempts"] = 0
                        user_lock["locked_until"] = None
                        
                if not is_locked:
                    db = next(get_db())
                    # Authenticacion real con Base de Datos
                    user = authenticate_user(db, email, password)
                    
                    if user:
                        # Reset attempts on success
                        user_lock["attempts"] = 0
                        user_lock["locked_until"] = None
                        lockout_data[username_key] = user_lock
                        save_lockout_data(lockout_data)
                        
                        # Minimalist Spinner
                        with boot_placeholder.container():
                            with st.spinner("Autenticando..."):
                                pass # sleep eliminado para mayor rapidez
                        
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
                        # LOG LOGIN
                        log_activity(user.email, "LOGIN", "Inicio de sesión exitoso")
                        st.rerun()
                    else:
                        user_lock["attempts"] += 1
                        if user_lock["attempts"] >= 3:
                            lock_time = datetime.now() + timedelta(minutes=5)
                            user_lock["locked_until"] = lock_time.isoformat()
                            alert_placeholder.error("MAXIMUM ATTEMPTS REACHED. TERMINAL LOCKED FOR 5 MINUTES.")
                        else:
                            attempts_left = 3 - user_lock["attempts"]
                            alert_placeholder.error(f"ACCESS DENIED: Invalid Operator ID or Authorization Code. Attempts remaining: {attempts_left}")
                        
                        lockout_data[username_key] = user_lock
                        save_lockout_data(lockout_data)

    # Footer removed per request
    pass

    
def logout():
    # LOG LOGOUT
    if st.session_state.user:
        log_activity(st.session_state.user['email'], "LOGOUT", "Cierre de sesión manual")
    
    # 1. Clear user state
    st.session_state.user = None
    st.session_state.logout_pending = True
    
    # 2. Invalidate session cookie directly via Javascript and reload page
    # This prevents the RerunException "red screen" and reliably clears the auth cookie
    import streamlit.components.v1 as components
    js_code = f"""
    <script>
        document.cookie = "{COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.parent.location.reload();
    </script>
    """
    components.html(js_code, height=0, width=0)
    
    # 3. Stop python execution so it doesn't crash proceeding components
    st.stop()

# 4. Control de flujo principal
if not st.session_state.user or st.session_state.get("logout_pending", False):
    login()
else:
    # 1. Restablecer la interfaz nativa + Custom Menu Labels
    st.markdown("""
        <style>
            [data-testid="stHeader"] {
                z-index: 1000000 !important;
                background: transparent !important;
                height: 3.5rem !important;
                pointer-events: none !important;
            }
            [data-testid="stHeader"] * {
                pointer-events: auto !important;
            }
            .stDeployButton, footer { display: none !important; }
            
            /* Reducción agresiva de bordes para que el dashboard se vea de pantalla completa */
            .main > div:first-child,
            .block-container,
            [data-testid="stAppViewBlockContainer"] {
                padding-top: 0rem !important;
                margin-top: -2.5rem !important;
                padding-bottom: 0rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                max-width: 100% !important;
            }
            
            /* Estilos para que los botones sean clickeables en su totalidad */
            #custom-nav-btn {
                display: inline-flex !important;
                align-items: center !important;
                gap: 8px !important;
                background: rgba(255,255,255,0.06) !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                border-radius: 8px !important;
                padding: 0 16px !important;
                height: 40px !important;
                color: #f0f6fc !important;
                width: auto !important;
                min-width: 110px !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
            }
            #custom-nav-btn:hover {
                background: rgba(255,255,255,0.12) !important;
                border-color: rgba(255,255,255,0.2) !important;
                transform: translateY(-1px);
            }
            .custom-label-text {
                font-size: 11px !important;
                font-weight: 800 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                pointer-events: none !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    import streamlit.components.v1 as components
    components.html("""
        <script>
            function updateMenuLabels() {
                const doc = window.parent.document;
                const buttons = doc.querySelectorAll('button');
                
                buttons.forEach(btn => {
                    const iconSpan = btn.querySelector('span[data-testid="stIconMaterial"]');
                    if (!iconSpan) return;
                    
                    const iconText = iconSpan.innerText.trim();
                    
                    // 1. Caso MENÚ (keyboard_double_arrow_right)
                    if (iconText === 'keyboard_double_arrow_right') {
                        if (!btn.querySelector('.custom-label-text')) {
                            btn.id = "custom-nav-btn";
                            const span = document.createElement('span');
                            span.innerText = 'MENÚ';
                            span.className = 'custom-label-text';
                            btn.appendChild(span);
                        }
                    }
                    
                    // 2. Caso CERRAR (keyboard_double_arrow_left)
                    if (iconText === 'keyboard_double_arrow_left') {
                        if (!btn.querySelector('.custom-label-text')) {
                            btn.id = "custom-nav-btn";
                            const span = document.createElement('span');
                            span.innerText = 'CERRAR';
                            span.className = 'custom-label-text';
                            btn.appendChild(span);
                        }
                    }
                });
            }
            
            const observer = new MutationObserver(updateMenuLabels);
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
            setInterval(updateMenuLabels, 500);
            updateMenuLabels();
        </script>
    """, height=0, width=0)

    # Sidebar con información de usuario y botón de salir
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['email']}**")
        if st.button("Cerrar Sesión", type="primary"):
            logout()
            st.stop()
        if st.session_state.config_warnings:
            with st.expander("⚠️ Avisos de configuración"):
                for w in st.session_state.config_warnings:
                    st.caption(w)
        st.divider()

    # --- Lógica de Navegación Dinámica por Rol ---
    user_email = st.session_state.user.get("email")
    user_role = st.session_state.user.get("role", "user").lower()
    
    pages = {}
    
    # 1. PERMISOS POR PROYECTO
    # Admin y Gerencia ven todo
    if user_role in ["admin", "gerencia"]:
        pages["Global"] = [
            st.Page("Hub_Testing.py", title="Command Hub", icon="🌍", default=True),
        ]
        pages["On Cloud"] = [
            st.Page("projects/OLR/Dashboard_ON.py", title="Dashboard ON", icon="👟"),
            st.Page("projects/OLR/Airport_Mode.py", title="Airport Mode ON", icon="✈️"),
        ]
        pages["Reebok"] = [
            st.Page("projects/Reebok/Dashboard_Reebok.py", title="Dashboard Reebok", icon="👟"),
            st.Page("projects/Reebok/Airport_Mode_Reebok.py", title="Airport Mode Reebok", icon="✈️"),
        ]
        pages["Ubicaciones"] = [
            st.Page("projects/Ubicaciones/Dashboard_Ubicaciones.py", title="Dashboard de Ubicaciones", icon="📍"),
        ]
    
    # Moderador de Reebok
    elif user_role in ["moderador_reebok", "moderador"]:
        pages["Reebok"] = [
            st.Page("projects/Reebok/Dashboard_Reebok.py", title="Dashboard Reebok", icon="👟", default=True),
            st.Page("projects/Reebok/Airport_Mode_Reebok.py", title="Airport Mode Reebok", icon="✈️"),
        ]
        
    # Moderador de ON
    elif user_role == "moderador_on":
        pages["On Cloud"] = [
            st.Page("projects/OLR/Dashboard_ON.py", title="Dashboard ON", icon="👟", default=True),
            st.Page("projects/OLR/Airport_Mode.py", title="Airport Mode ON", icon="✈️"),
        ]

    # 2. SECCIÓN EXCLUSIVA PARA EL ADMIN SUPREMO (Email 'admin')
    if user_email == "admin":
        pages["Control Maestro"] = [
            st.Page("auth_system/user_management.py", title="Usuarios y Permisos", icon="🛡️"),
            st.Page("pages/audit_log.py", title="Registro de Actividad", icon="📜")
        ]

    # Si por alguna razón no hay páginas (no debería pasar), mostrar error
    if not pages:
        st.error("Tu cuenta no tiene permisos asignados. Contacta al administrador.")
        st.stop()

    pg = st.navigation(pages)
    pg.run()
