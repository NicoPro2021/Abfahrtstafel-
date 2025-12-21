import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # Jetzt mit 5 Stunden Vorschau (duration=300)
    url = "https://v6.db.transport.rest/stops/8006654/departures?duration=300&results=20"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        # Zerbst-relevante Ziele
        zerbst_ziele = ["Magdeburg", "Dessau", "Leipzig", "Bitterfeld", "Güterglück", "Lutherstadt"]
        
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            ziel = dep.get('direction', 'Unbekannt')
            
            # Filter: Nur echte Zerbster Richtungen
            if not any(z in ziel for z in zerbst_ziele):
                continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            gleis = str(dep.get('platform') or "-")
            
            delay = dep.get('delay')
            info_text = "pünktlich"
            if delay and delay > 0:
                info_text = f"+{int(delay/60)}"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        if not fahrplan:
            return [{"zeit": "Warten", "linie": "DB", "ziel": "Nächster Zug...", "gleis": "-", "info": u_zeit}]

        return fahrplan[:8]

    except Exception:
        return [{"zeit": "Error", "linie": "Bot", "ziel": "Verbindung", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
