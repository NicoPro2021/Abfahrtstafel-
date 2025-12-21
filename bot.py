import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # ID 8010404 ist der "Knoten" für Zerbst/Anhalt
    url = "https://v6.db.transport.rest/stops/8010404/departures?duration=120&results=15"
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": "Error", "gleis": "-", "info": u_zeit}]
        
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Wir lassen nur die Züge durch, die in Zerbst halten
            # RE13 (Magdeburg/Leipzig) und RB42 (Magdeburg/Dessau)
            if not any(x in linie for x in ["RE13", "RB42"]):
                continue
            
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")
            ziel = dep.get('direction', 'Ziel unbekannt')
            
            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": "pünktlich"
            })

        if not fahrplan:
            return [{"zeit": "INFO", "linie": "DB", "ziel": "Warte auf RE13", "gleis": "-", "info": u_zeit}]

        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
