import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Wir nutzen die DB-HAFAS Schnittstelle über einen stabilen Endpoint
    STATION_ID = "8006654"
    url = f"https://db.transport.rest/stops/{STATION_ID}/departures?results=6&duration=120"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
        'Accept': 'application/json'
    }

    try:
        # Wir fügen einen Cache-Buster hinzu, um keine alten Daten zu laden
        response = requests.get(f"{url}&t={int(datetime.now().timestamp())}", headers=headers, timeout=15)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # Manche Server liefern die Liste direkt, manche im Feld 'departures'
        items = data.get('departures', data) if isinstance(data, dict) else data
        
        fahrplan = []
        jetzt_zeit = datetime.now().strftime("%H:%M")

        for dep in items:
            # Zeit extrahieren
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            
            # Linie und Ziel
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            ziel = dep.get('direction', 'Unbekannt')
            
            # Filter gegen Kassel-Testdaten
            if "RT" in linie or "Wolfhagen" in ziel:
                continue

            gleis = str(dep.get('platform') or "-")
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": info,
                "update": jetzt_zeit
            })

        if not fahrplan:
            return [{"zeit": "00:00", "linie": "DB", "ziel": "Nächste Züge...", "gleis": "-", "info": jetzt_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
