import streamlit as st
from database import engine, Base, get_db
from models import User
from auth import authenticate_user, register_user

# 1. Configuración de página
st.set_page_config(page_title="Sistema de Autenticación", page_icon="🔒")

# 2. Inicializar base de datos (crear tablas si no existen)
Base.metadata.create_all(bind=engine)

# 3. Gestión de sesión
if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("Iniciar Sesión")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            db = next(get_db())
            user = authenticate_user(db, email, password)
            if user:
                st.session_state.user = {
                    "email": user.email,
                    "role": user.role
                }
                st.rerun()
            else:
                st.error("Credenciales incorrectas o cuenta bloqueada.")

def logout():
    st.session_state.user = None
    st.rerun()

def dashboard():
    st.title(f"Bienvenido, {st.session_state.user['email']}")
    st.write("Has accedido al dashboard protegido.")
    
    # Botón de logout en la barra lateral
    with st.sidebar:
        st.write(f"Usuario: {st.session_state.user['email']}")
        st.write(f"Rol: {st.session_state.user['role']}")
        if st.button("Cerrar Sesión"):
            logout()

    # Área de Admin (Solo si el rol es admin)
    if st.session_state.user['role'] == 'admin':
        st.divider()
        st.header("Panel de Administración")
        st.write("Registrar nuevo usuario")
        
        with st.form("register_form"):
            new_email = st.text_input("Nuevo Email")
            new_password = st.text_input("Nueva Contraseña", type="password")
            new_role = st.selectbox("Rol", ["user", "admin"])
            submit_reg = st.form_submit_button("Registrar Usuario")
            
            if submit_reg:
                db = next(get_db())
                try:
                    register_user(db, new_email, new_password, new_role)
                    st.success(f"Usuario {new_email} creado exitosamente.")
                except ValueError as e:
                    st.error(str(e))

# 4. Control de flujo principal
def main():
    if st.session_state.user:
        dashboard()
    else:
        login()
        # Nota: En un sistema real, el primer usuario admin se crearía manualmente en BD 
        # o mediante un script de setup inicial.

if __name__ == "__main__":
    main()
