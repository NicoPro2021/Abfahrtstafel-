import subprocess
import time
import os

# Die Liste deiner 10 vorhandenen Bots
bots = [
    "zerbst_bot.py", 
    "rodleben_bot.py", 
    "rosslau_bot.py", 
    "dessau_hbf_bot.py", 
    "dessau_sued_bot.py", 
    "biederitz_bot.py",
    "magdeburg_hbf_bot.py", 
    "magdeburg_neustadt_bot.py", 
    "magdeburg_herrenkrug_bot.py", 
    "leipzig_hbf_bot.py"
]

def run_cycle():
    print(f"--- Zyklus gestartet um {time.strftime('%H:%M:%S')} ---")
    for bot in bots:
        if os.path.exists(bot):
            print(f"Aktualisiere: {bot}")
            # Startet deinen vorhandenen Bot
            subprocess.run(["python", bot])
            
            # WICHTIG: 5 Sekunden Pause für die API nach jedem Bahnhof
            time.sleep(5) 
        else:
            print(f"Datei nicht gefunden: {bot}")
    print("--- Zyklus beendet ---")

if __name__ == "__main__":
    run_cycle()
