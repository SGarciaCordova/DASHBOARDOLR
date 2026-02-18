import schedule
import time
import subprocess
import logging
import random
import os
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='bot_launcher.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Configuration
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_SCRIPT = os.path.join(PROJECT_DIR, "projects", "Reebok", "wms_scraper.py")
UNIFIER_SCRIPT = os.path.join(PROJECT_DIR, "projects", "Reebok", "unificador.py")
PYTHON_EXEC = sys.executable

# Schedule Times (24h format)
SCHEDULE_TIMES = ["08:00", "13:00", "18:00"]

def run_bot(scheduled_time):
    logging.info(f"--- Job scheduled for {scheduled_time} started ---")
    
    # Add Jitter (Random delay between 0 and 15 minutes)
    delay_seconds = random.randint(0, 900)
    logging.info(f"Applying jitter: Waiting {delay_seconds} seconds before execution...")
    time.sleep(delay_seconds)
    
    # 1. Run Scraper
    logging.info(f"Launching Scraper: {SCRAPER_SCRIPT}")
    try:
        result_scraper = subprocess.run(
            [PYTHON_EXEC, SCRAPER_SCRIPT], 
            capture_output=True, 
            text=True,
            check=False
        )
        if result_scraper.returncode == 0:
            logging.info("Scraper finished successfully.")
            # Log output header if needed, or just rely on scraper's own logging (which goes to console/file)
        else:
            logging.error(f"Scraper failed with return code {result_scraper.returncode}")
            logging.error(f"Stderr: {result_scraper.stderr}")
            return # Stop if scraper fails
            
    except Exception as e:
        logging.error(f"Exception trying to run scraper: {e}")
        return

    # 2. Run Unifier
    logging.info(f"Launching Unifier: {UNIFIER_SCRIPT}")
    try:
        result_unifier = subprocess.run(
            [PYTHON_EXEC, UNIFIER_SCRIPT], 
            capture_output=True, 
            text=True,
            check=False
        )
        if result_unifier.returncode == 0:
            logging.info("Unifier finished successfully.")
        else:
            logging.error(f"Unifier failed with return code {result_unifier.returncode}")
            logging.error(f"Stderr: {result_unifier.stderr}")
            
    except Exception as e:
        logging.error(f"Exception trying to run unifier: {e}")

    logging.info("--- Job Cycle Complete ---")

def main():
    logging.info("Bot Launcher Initialized.")
    logging.info(f"Scheduled times: {SCHEDULE_TIMES}")
    logging.info(f"Target Scripts:\n - Scraper: {SCRAPER_SCRIPT}\n - Unifier: {UNIFIER_SCRIPT}")

    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(run_bot, t)
        
    logging.info("Waiting for next schedule...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
