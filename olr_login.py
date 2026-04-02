import streamlit as st
from datetime import datetime, timedelta
import time
import hashlib
import json
import os

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

# ------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------
st.set_page_config(
    page_title="OLR Command Center - Auth",
    page_icon="terminal",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ------------------------------------------------------------------------
# CUSTOM CSS STYLE INJECTION
# ------------------------------------------------------------------------
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');

        /* Global Theme - Deep Dark */
        [data-testid="stAppViewContainer"], .stApp {
            background-color: #0d1117 !important;
            font-family: 'Inter', sans-serif !important;
            color: #c9d1d9 !important;
        }

        /* Mono font for technical bits */
        .mono { font-family: 'Share Tech Mono', monospace !important; }

        /* Hide Streamlit elements */
        [data-testid="stHeader"] {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stDeployButton {display: none !important;}
        
        /* THE COMMAND HUB BOX (Login Form) */
        [data-testid="stForm"] {
            border: 2px solid #58a6ff !important;
            padding: 50px 40px !important;
            background-color: #161b22 !important;
            box-shadow: 0 0 30px rgba(88, 166, 255, 0.15), inset 0 0 20px rgba(88, 166, 255, 0.05) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px);
        }

        /* NEON HEADING */
        h1 {
            background: linear-gradient(135deg, #79c0ff, #58a6ff) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 15px rgba(88, 166, 255, 0.5) !important;
            font-size: 1.8rem !important;
            text-transform: uppercase;
            letter-spacing: 3px;
            font-weight: 800 !important;
            text-align: center;
            margin-bottom: 5px !important;
        }
        
        .subtitle {
            color: #d2a8ff !important;
            text-shadow: 0 0 10px rgba(210, 168, 255, 0.4);
            font-size: 0.8rem;
            text-align: center;
            letter-spacing: 2px;
            font-weight: 700;
            margin-bottom: 30px;
            text-transform: uppercase;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 15px;
        }

        /* SYSTEM STATUS NEON */
        .status-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: -10px;
            margin-bottom: 35px;
            font-family: 'Share Tech Mono', monospace;
        }
        .status-indicator {
            color: #3fb950 !important;
            text-shadow: 0 0 12px rgba(63, 185, 80, 0.6) !important;
            font-weight: bold;
            font-size: 0.85rem;
            animation: pulse 1.5s infinite alternate;
        }
        @keyframes pulse {
            from { opacity: 0.7; text-shadow: 0 0 8px rgba(63, 185, 80, 0.4); }
            to { opacity: 1; text-shadow: 0 0 15px rgba(63, 185, 80, 0.8); }
        }
        .timestamp {
            color: #8b949e;
            font-size: 0.75rem;
        }

        /* INPUT FIELDS - NEON BLUE */
        .stTextInput label {
            color: #58a6ff !important;
            text-shadow: 0 0 8px rgba(88, 166, 255, 0.5) !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 8px;
        }
        .stTextInput > div > div > input {
            background-color: #0d1117 !important;
            color: #f0f6fc !important;
            border: 1px solid #30363d !important;
            border-radius: 8px !important;
            padding: 12px 18px !important;
            font-family: 'Share Tech Mono', monospace !important;
            font-size: 1rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .stTextInput > div > div > input:focus {
            border-color: #58a6ff !important;
            box-shadow: 0 0 15px rgba(88, 166, 255, 0.3) !important;
            background-color: #161b22 !important;
        }

        /* BUTTON - NEON GLOW-IN */
        [data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            background: linear-gradient(135deg, #1f6feb, #58a6ff) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 18px 0 !important;
            font-weight: 800 !important;
            font-size: 1.2rem !important;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-top: 20px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(31, 111, 235, 0.3) !important;
        }
        [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 25px rgba(88, 166, 255, 0.6) !important;
            background: linear-gradient(135deg, #388bfd, #79c0ff) !important;
        }
        
        /* ERROR ALERT NEON RED */
        [data-testid="stAlert"] {
            background-color: rgba(248, 81, 73, 0.05) !important;
            border: 1px solid #f85149 !important;
            box-shadow: 0 0 10px rgba(248, 81, 73, 0.2) !important;
            border-radius: 8px !important;
        }
        [data-testid="stAlert"] p {
            color: #ff7baf !important;
            text-shadow: 0 0 8px rgba(255, 123, 175, 0.5) !important;
            font-family: 'Share Tech Mono', monospace !important;
            font-weight: 700;
        }
        
        /* FOOTER */
        .system-footer {
            position: fixed;
            bottom: 25px;
            left: 0;
            width: 100%;
            text-align: center;
            color: #484f58;
            font-size: 0.7rem;
            letter-spacing: 2px;
            font-family: 'Share Tech Mono', monospace;
            z-index: 100;
        }
        .session-neon {
            color: #ffa657 !important;
            text-shadow: 0 0 8px rgba(255, 166, 87, 0.5) !important;
            font-size: 0.65rem;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------------
# LOGIC & RENDER
# ------------------------------------------------------------------------
def main():
    inject_custom_css()

    # Initializing session state for auth
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        # Initialize a unique session ID hash on first load
        st.session_state.session_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16].upper()
    if not st.session_state.authenticated:
        # Extra spacing from top for vertical centering
        st.write("<br><br><br>", unsafe_allow_html=True)
        
        # Center constraint using columns
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Login Form container
            with st.form("login_form", clear_on_submit=False):
                # Title & Subtitle
                st.markdown("<h1>OLR Operations Command Center</h1>", unsafe_allow_html=True)
                st.markdown('<div class="subtitle">3PL CONTROL TOWER — INTERNAL ACCESS ONLY</div>', unsafe_allow_html=True)
                
                # Real-time System Status Indicator
                # Note: Time is initialized dynamically when page loads
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                st.markdown(f'''
                    <div class="status-container">
                        <span class="status-indicator">● SYSTEM OPERATIONAL</span>
                        <span class="timestamp">{current_time}</span>
                    </div>
                ''', unsafe_allow_html=True)

                # Custom fields
                username = st.text_input("Operator ID", key="user_input")
                password = st.text_input("Authorization Code", type="password", key="pass_input")
                
                # Placeholders for boot sequence and alerts
                alert_placeholder = st.empty()
                boot_placeholder = st.empty()
                
                # Submit action
                submit = st.form_submit_button("Initialize Uplink")
                
                if submit:
                    # Avoid polluting log with empty inputs
                    username_key = username.strip()
                    if not username_key:
                        alert_placeholder.error("ACCESS DENIED: Invalid Operator ID.")
                        st.stop()
                        
                    lockout_data = get_lockout_data()
                    user_lock = lockout_data.get(username_key, {"attempts": 0, "locked_until": None})
                    
                    # Check if locked out persistently
                    is_locked = False
                    if user_lock["locked_until"]:
                        locked_time = datetime.fromisoformat(user_lock["locked_until"])
                        if datetime.now() < locked_time:
                            is_locked = True
                            remaining_time = int((locked_time - datetime.now()).total_seconds())
                            alert_placeholder.error(f"SYSTEM LOCKOUT IN EFFECT. TERMINAL SECURED.\\nContact Supervisor. Retry available in {remaining_time} seconds.")
                        else:
                            # Lockout expired, reset for this user
                            user_lock["attempts"] = 0
                            user_lock["locked_until"] = None
                            
                    if not is_locked:
                        # TODO: replace with auth.py verification call
                        is_authenticated = False
                        
                        if is_authenticated:
                            # Reset attempts on success
                            user_lock["attempts"] = 0
                            user_lock["locked_until"] = None
                            lockout_data[username_key] = user_lock
                            save_lockout_data(lockout_data)
                            
                            # Boot Sequence
                            boot_text = ""
                            sequence = [
                                "> INITIATING SECURE HANDSHAKE... [OK]",
                                "> VERIFYING OPERATOR CLEARANCE... [OK]",
                                "> DECRYPTING UPLINK PACKETS... [OK]",
                                "> ESTABLISHING DIRECTIVES... [OK]",
                                "> ACCESS GRANTED."
                            ]
                            
                            for step in sequence:
                                boot_text += f"<div style='color: #00ff00; font-family: \"Share Tech Mono\", monospace; font-size: 0.85rem; margin-bottom: 5px;'>{step}</div>"
                                boot_placeholder.markdown(f"<div style='background-color: #05070d; border: 1px solid #1a2436; padding: 15px; margin-top: 20px;'>{boot_text}</div>", unsafe_allow_html=True)
                                time.sleep(0.4)
                            
                            time.sleep(0.5)
                            st.session_state.authenticated = True
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
                        
        # Render bottom footer
        st.markdown(f'''
            <div class="system-footer">
                v2.1.4 — Build 2024.11 | <span class="session-neon">OLR Logistics Engine</span><br>
                <span class="session-neon" style="font-size: 0.65rem;">SESSION ID: {st.session_state.session_hash} — ALL ACTIVITY IS RECORDED</span>
            </div>
        ''', unsafe_allow_html=True)
        
    else:
        # Dashboard view once logged in (Placeholder)
        st.write("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1>ACCESS GRANTED</h1>", unsafe_allow_html=True)
        st.markdown("<div class='status-indicator' style='text-align:center; font-size: 1.1rem; margin-top:20px;'>● UPLINK ESTABLISHED. Welcome to the Control Tower.</div>", unsafe_allow_html=True)
        
        # Logout button to terminate session
        st.write("<br><br>", unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1.5, 1, 1.5])
        with btn_col:
            if st.button("TERMINATE SESSION"):
                st.session_state.authenticated = False
                st.rerun()

if __name__ == "__main__":
    main()
