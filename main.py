import subprocess
import time
import os

bots = [
    "zerbst_bot.py", "rodleben_bot.py", "rosslau_bot.py", 
    "dessau_hbf_bot.py", "dessau_sued_bot.py", "biederitz_bot.py",
    "magdeburg_hbf_bot.py", "magdeburg_neustadt_bot.py", 
    "magdeburg_herrenkrug_bot.py", "leipzig_hbf_bot.py"
]

def run_cycle():
    print(f"--- Zyklus-Start: {time.strftime('%H:%M:%S')} ---")
    for bot in bots:
        if os.path.exists(bot):
            print(f"Abruf: {bot}")
            subprocess.run(["python", bot])
            # 4 Sekunden Pause ist der 'Sweet Spot' für 60s Gesamtdauer
            time.sleep(4) 
        else:
            print(f"Fehlt: {bot}")
    print(f"--- Zyklus-Ende ---")

if __name__ == "__main__":
    run_cycle()
