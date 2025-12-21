import requests
import json
import time
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    # Direkter Link zu Zerbst/Anhalt
    url = "https://v6.db.transport.rest/stops/8010405/departures?results=15&duration=240"
    
    # Wir geben uns als normaler Browser aus (User-Agent), damit wir nicht blockiert werden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Wir versuchen es 3 Mal hintereinander
    for i in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            departures = data.get('departures', [])
            fahrplan = []

            for dep in departures:
                # Linie extrahieren (z.B. RE13)
                linie = dep.get('line', {}).get('name', '???').replace(" ", "")
                if "Bus" in linie: continue 

                zeit_roh = dep.get('when') or dep.get('plannedWhen')
                if not zeit_roh: continue
                
                soll_zeit = zeit_roh.split('T')[1][:5]
                ziel = dep.get('direction', 'Ziel')[:15]
                gleis = str(dep.get('platform') or "-")
                
                delay = dep.get('delay')
                info = f"+{int(delay/60)}" if delay and delay >= 60 else ""

                fahrplan.append({
                    "zeit": soll_zeit,
                    "linie": linie,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info,
                    "update": u_zeit
                })
            
            if not fahrplan:
                return [{"zeit": u_zeit, "linie": "INFO", "ziel": "Kein Zug", "gleis": "-", "info": ""}]
            
            return fahrplan[:10]

        except Exception as e:
            print(f"Fehler beim Versuch {i+1}: {e}")
            time.sleep(10) # 10 Sekunden warten vor Neustart
            
    return [{"zeit": "Err", "linie": "Bot", "ziel": "API-Timeout", "gleis": "-", "info": "Retry", "update": u_zeit}]

if __name__ == "__main__":
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
