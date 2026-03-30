import json
import os
from datetime import datetime
import pytz

def inject_funcs():
    with open("projects/Reebok/Dashboard_Reebok.py", "r", encoding="utf-8") as f:
        text = f.read()

    replacement_func = """
def get_cooldown_status(minutes):
    try:
        from sqlalchemy import text
        import pytz
        from datetime import datetime
        import os
        import json
        CDMX_TZ_LOCAL = pytz.timezone('America/Mexico_City')
        
        with engine.connect() as conn:
            result = conn.execute(text('SELECT "timestamp" FROM audit_logs WHERE event_type = \\'SYNC\\' ORDER BY "timestamp" DESC LIMIT 1')).fetchone()
            if not result:
                return True, 0
            
            last_run_raw = result[0]
            if last_run_raw.tzinfo is None:
                last_run_cdmx = pytz.utc.localize(last_run_raw).astimezone(CDMX_TZ_LOCAL)
            else:
                last_run_cdmx = last_run_raw.astimezone(CDMX_TZ_LOCAL)
                
            now_cdmx = datetime.now(CDMX_TZ_LOCAL)
            elapsed = now_cdmx - last_run_cdmx
            elapsed_minutes = elapsed.total_seconds() / 60
            
            if elapsed_minutes < minutes:
                return False, round(minutes - elapsed_minutes, 1)
            else:
                return True, 0
    except Exception as e:
        import os
        import json
        from datetime import datetime
        cooldown_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_cooldown.json")
        if not os.path.exists(cooldown_file): return True, 0
        try:
            with open(cooldown_file, "r") as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data.get("last_run"))
                now = datetime.now()
                elapsed = now - last_run
                elapsed_minutes = elapsed.total_seconds() / 60
                if elapsed_minutes < minutes: return False, round(minutes - elapsed_minutes, 1)
        except: pass
        return True, 0

def save_last_run_now():
    import os
    import json
    from datetime import datetime
    cooldown_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_cooldown.json")
    try:
        with open(cooldown_file, "w") as f:
            json.dump({"last_run": datetime.now().isoformat()}, f)
    except Exception:
        pass
"""

    idx = text.find("@st.cache_data(ttl=86400")
    if idx != -1:
        new_text = text[:idx] + replacement_func + "\n\n" + text[idx:]
        with open("projects/Reebok/Dashboard_Reebok.py", "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Fixed!")
    else:
        print("Not found")

if __name__ == "__main__":
    inject_funcs()
