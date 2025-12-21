import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # STATION ID FÜR ZERBST: 8010405 (DIREKT IM LINK)
    url = "https://v6.db.transport.rest/stops/8010405/departures?results=10&duration=240"

    try:
        # Wir erzwingen eine frische Verbindung ohne Cache
        headers = {'Cache-Control': 'no-cache', 'User-Agent': 'Zerbst-Monitor-V1'}
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        if not departures:
            return [{"zeit": u_zeit, "linie": "INFO", "ziel": "Kein Zug", "gleis": "-", "info": ""}]

        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "Bus" in linie: continue 

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            soll_zeit = zeit_roh.split('T')[1][:5]
            ziel = dep.get('direction', 'Ziel')[:15]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung
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
    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Fehler"}]

if __name__ == "__main__":
    # Wir überschreiben die daten.json gnadenlos
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
