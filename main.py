import subprocess
import time
import os
import json

bots = [
    "zerbst_bot.py", "rodleben_bot.py", "rosslau_bot.py", 
    "dessau_hbf_bot.py", "dessau_sued_bot.py", "biederitz_bot.py",
    "magdeburg_hbf_bot.py", "magdeburg_neustadt_bot.py", 
    "magdeburg_herrenkrug_bot.py", "leipzig_hbf_bot.py"
]

def check_json_valid(filename):
    """Prüft, ob die Datei existiert und nicht nur [] enthält."""
    if not os.path.exists(filename): return False
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return len(data) > 0
    except: return False

def run_cycle():
    print(f"--- Start: {time.strftime('%H:%M:%S')} ---")
    fehler_count = 0

    for bot in bots:
        json_file = bot.replace("_bot.py", ".json")
        if os.path.exists(bot):
            subprocess.run(["python", bot])
            
            # Prüfen, ob Bot Erfolg hatte oder [] lieferte
            if not check_json_valid(json_file):
                print(f"!!! API BLOCKADE bei {bot} !!!")
                fehler_count += 1
            
            # 4 Sekunden Pause zwischen den Bots (für 60s Takt)
            time.sleep(4)
        
    # Wenn mehr als 3 Bots leer waren, API-Pause einlegen
    if fehler_count > 3:
        print("Zu viele Fehler. API braucht Ruhe. Warte 30s zusätzlich...")
        time.sleep(30)

if __name__ == "__main__":
    run_cycle()
