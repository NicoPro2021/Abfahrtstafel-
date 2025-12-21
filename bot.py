import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Deutsche Zeit erzwingen
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # STATION ID FÜR ZERBST/ANHALT: 8010405
    # (Wannsee wäre 8010358 - wir nutzen hier 8010405!)
    url = "https://v6.db.transport.rest/stops/8010405/departures?results=15&duration=240&remarks=true"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "Bus" in linie: continue # Keine Busse

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
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
        return fahrplan[:10]
    except:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Zerbst-Error", "gleis": "-", "info": "", "update": u_zeit}]

if __name__ == "__main__":
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
