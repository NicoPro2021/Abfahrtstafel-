import subprocess
import time
import os

# Die Liste deiner 10 einzelnen Bot-Dateien
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

def update_alle_stationen():
    print(f"--- Starte Update-Zyklus: {time.strftime('%H:%M:%S')} ---")
    
    for bot_file in bots:
        if os.path.exists(bot_file):
            print(f"Rufe Daten ab: {bot_file}")
            
            # Startet den jeweiligen Bot
            subprocess.run(["python", bot_file])
            
            # WICHTIG: 5 Sekunden Pause zwischen den Stationen. 
            # Das verhindert, dass die Bahn-API dich wegen zu vieler Anfragen sperrt.
            time.sleep(5)
        else:
            print(f"WARNUNG: Datei {bot_file} wurde nicht gefunden.")
            
    print(f"--- Zyklus beendet: {time.strftime('%H:%M:%S')} ---")

if __name__ == "__main__":
    update_alle_stationen()
