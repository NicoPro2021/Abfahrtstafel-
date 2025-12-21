import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # HAFAS Zerbst/Anhalt ID: 8006654 oder direkt über den Namen
    # Wir nutzen hier den dedizierten Zerbst-Endpunkt
    url = "https://db.transport.rest/stops/8006654/departures?duration=180&remarks=true&results=15"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": "Server Busy", "gleis": "-", "info": u_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # WICHTIG: Filter gegen den Kassel-Fehler
            if "RT" in linie or "Kassel" in dep.get('direction', ''):
                continue

            # Zeit & Ziel
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung & Gründe
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                info_text = f"+{int(delay/60)} {grund}".strip()
            elif grund:
                info_text = grund

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:35],
                "update": u_zeit
            })

        if not fahrplan:
            return [{"zeit": "Check", "linie": "DB", "ziel": "Kein Zug gef.", "gleis": "-", "info": u_zeit}]

        return fahrplan[:8] # Die nächsten 8 echten Zerbster Züge

    except Exception as e:
        return [{"zeit": "Error", "linie": "Bot", "ziel": "Retry...", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
