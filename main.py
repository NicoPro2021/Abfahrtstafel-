import os
import subprocess
import time
import sys

# Deine 10 Stationen
BOTS = [
    "zerbst_bot.py", "rodleben_bot.py", "rosslau_bot.py", 
    "dessau_hbf_bot.py", "dessau_sued_bot.py", "biederitz_bot.py",
    "magdeburg_hbf_bot.py", "magdeburg_neustadt_bot.py", 
    "magdeburg_herrenkrug_bot.py", "leipzig_hbf_bot.py"
]

def run_updates():
    print(f"--- Update-Zyklus gestartet: {time.strftime('%H:%M:%S')} ---")
    
    for bot in BOTS:
        if os.path.exists(bot):
            # Schutz: Kurze Pause zwischen den Bots (verhindert API-Spikes)
            time.sleep(1.5)
            
            print(f"Aktualisiere: {bot}...")
            result = subprocess.run(["python", bot], capture_output=True, text=True)
            
            # Falls ein Bot einen API-Fehler (429) meldet, stoppen wir sofort
            if "429" in result.stderr or "429" in result.stdout:
                print("KRITISCH: API-Limit erreicht. Breche Zyklus ab.")
                sys.exit(1)
        else:
            print(f"Datei {bot} nicht gefunden – überspringe.")

if __name__ == "__main__":
    run_updates()
