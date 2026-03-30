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
        /* Import a technical/mono font from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

        /* Global background and font */
        [data-testid="stAppViewContainer"], .stApp {
            background-color: #0A0E1A !important;
            font-family: 'Share Tech Mono', monospace !important;
            color: #8A9BB0 !important;
        }

        /* Hide default Streamlit UI elements completely */
        [data-testid="stHeader"] {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stDeployButton {display: none !important;}
        
        /* Container styling to act as the central control box */
        [data-testid="stForm"] {
            border: 1px solid #00AEEF !important;
            padding: 40px 30px !important;
            background: linear-gradient(180deg, rgba(10,14,26,1) 0%, rgba(15,22,40,1) 100%) !important;
            box-shadow: 0 0 20px rgba(0, 174, 239, 0.15), inset 0 0 15px rgba(0, 174, 239, 0.05) !important;
            border-radius: 2px !important;
            position: relative;
        }

        /* Titles and headers */
        h1 {
            color: #00AEEF !important;
            font-size: 1.6rem !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(0,174,239,0.5);
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
            text-align: center;
        }
        
        .subtitle {
            color: #8A9BB0;
            font-size: 0.85rem;
            text-align: center;
            margin-top: 5px;
            letter-spacing: 1px;
            border-bottom: 1px solid #1a2436;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }

        /* Status Indicator Row */
        .status-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: -15px;
            margin-bottom: 30px;
            font-size: 0.8rem;
            font-family: 'Share Tech Mono', monospace;
        }
        .status-indicator {
            color: #00ff00;
            text-shadow: 0 0 5px rgba(0,255,0,0.6);
            /* simple CSS blink animation */
            animation: blinker 2s linear infinite;
        }
        @keyframes blinker {
            50% { opacity: 0.6; text-shadow: none; }
        }
        .timestamp {
            color: #4a5a6b;
        }

        /* Text Input Fields */
        .stTextInput > div > div > input {
            background-color: #05070d !important;
            color: #00AEEF !important;
            border: 1px solid #1a2436 !important;
            border-radius: 2px !important;
            padding: 10px 15px !important;
            font-family: 'Share Tech Mono', monospace !important;
            transition: all 0.3s ease;
        }
        .stTextInput > div > div > input:focus {
            border-color: #00AEEF !important;
            box-shadow: 0 0 8px rgba(0,174,239,0.3) !important;
            outline: none !important;
        }
        .stTextInput label {
            color: #8A9BB0 !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        /* Login Button */
        [data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            background-color: transparent !important;
            color: #00AEEF !important;
            border: 1px solid #00AEEF !important;
            border-radius: 2px !important;
            padding: 15px 0 !important;
            font-family: 'Share Tech Mono', monospace !important;
            font-size: 1.1rem !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 25px !important;
            transition: all 0.2s ease-in-out !important;
            position: relative;
            overflow: hidden;
        }
        [data-testid="stFormSubmitButton"] > button:hover {
            background-color: #00AEEF !important;
            color: #0A0E1A !important;
            box-shadow: 0 0 15px #00AEEF !important;
            border: 1px solid #00AEEF !important;
        }
        
        [data-testid="stFormSubmitButton"] > button:active {
            transform: scale(0.98);
        }

        /* Alerts and Errors Override */
        [data-testid="stAlert"] {
            background-color: rgba(255, 0, 0, 0.05) !important;
            border: 1px solid #ff0000 !important;
            color: #ff0000 !important;
            border-radius: 2px !important;
        }
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
            color: #ff0000 !important;
            font-family: 'Share Tech Mono', monospace !important;
            font-size: 0.85rem !important;
        }
        
        /* Footer Absolute Positioning */
        .system-footer {
            position: fixed;
            bottom: 20px;
            left: 0;
            width: 100%;
            text-align: center;
            color: #4a5a6b;
            font-size: 0.75rem;
            letter-spacing: 1px;
            font-family: 'Share Tech Mono', monospace;
            z-index: 100;
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
                v2.1.4 — Build 2024.11 | OLR Logistics Engine<br>
                <span style="color: #00AEEF; font-size: 0.65rem;">SESSION ID: {st.session_state.session_hash} — ALL ACTIVITY IS RECORDED</span>
            </div>
        ''', unsafe_allow_html=True)
        
    else:
        # Dashboard view once logged in (Placeholder)
        st.write("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;'>ACCESS GRANTED</h1>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; color:#00ff00; margin-top:20px;'>● UPLINK ESTABLISHED. Welcome to the Control Tower.</div>", unsafe_allow_html=True)
        
        # Logout button to terminate session
        st.write("<br><br>", unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1.5, 1, 1.5])
        with btn_col:
            if st.button("TERMINATE SESSION"):
                st.session_state.authenticated = False
                st.rerun()

if __name__ == "__main__":
    main()
