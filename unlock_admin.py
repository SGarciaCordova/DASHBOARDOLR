import sys
import json
import os
import getpass
from datetime import datetime
import streamlit as st

LOCKOUT_FILE = "lockout_registry.json"
LOG_FILE = "unlock_attempts.log"

def log_attempt(status, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {status}: {message}\n")

def main():
    print("=========================================")
    print(" OLR COMMAND CENTER - EMERGENCY OVERRIDE ")
    print("=========================================")
    
    # Allows passing Username as Argument (e.g. python unlock_admin.py usuario1)
    if len(sys.argv) > 1:
        target_user = sys.argv[1]
    else:
        target_user = input("Operator ID to unlock [default: admin]: ").strip()
        if not target_user:
            target_user = "admin"
            
    try:
        # Tries to retrieve key from standard Streamlit secrets manager
        expected_key = st.secrets.get("recovery_key")
        if not expected_key:
            print("ERROR: 'recovery_key' is not defined in Streamlit secrets.")
            sys.exit(1)
    except FileNotFoundError:
        print("ERROR: .streamlit/secrets.toml file not found.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR reading secrets: {e}")
        sys.exit(1)

    # getpass hides the typed string from the console
    entered_key = getpass.getpass("Enter RECOVERY_KEY: ")

    if entered_key == expected_key:
        print("\n[OK] CLEARANCE ACCEPTED.")
        print(f"Executing emergency override for Operator ID: {target_user}...")
        
        # Read the current registry
        if os.path.exists(LOCKOUT_FILE):
            try:
                with open(LOCKOUT_FILE, "r") as f:
                    registry = json.load(f)
            except json.JSONDecodeError:
                registry = {}
        else:
            registry = {}
            
        # Option: Remove the user entirely from the locked list
        if target_user in registry:
            del registry[target_user]
            action = "removed from lockout registry"
        else:
            action = "not found in lockout registry (already clear)"
            
        # Write back changes
        try:
            with open(LOCKOUT_FILE, "w") as f:
                json.dump(registry, f, indent=4)
            print(f"> [{action.upper()}] Operation Complete.")
            
            # Log successful override
            log_attempt("SUCCESS", f"Developer override initiated. '{target_user}' {action}.")
            
        except Exception as e:
            print(f"ERROR WRITING TO REGISTRY: {e}")
            sys.exit(1)
            
    else:
        print("\n[!] ACCESS DENIED. UNAUTHORIZED OVERRIDE ATTEMPT.")
        # Log failure
        log_attempt("FAILED", f"Invalid recovery key attempt for target '{target_user}'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
