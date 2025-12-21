import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir erzwingen Zerbst über den Parameter ?stop=...
# Die ID 8006654 ist Zerbst/Anhalt
URL = "https://v6.db.transport.rest/stops/8006654/departures?results=6&duration=120"

def hole_daten():
    try:
        # User-Agent mitschicken, damit die DB uns als Browser sieht
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        jetzt = datetime.now().strftime("%H:%M:%S")

        for dep in departures:
            # Zeit
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw else "--:--"
            
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???')
            
            # Ziel
            ziel = dep.get('direction', 'Unbekannt')
            
            # Gleis
            gleis = dep.get('platform') or "-"
            
            # Verspätung
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": str(gleis),
                "info": info,
                "update": jetzt
            })

        if not fahrplan:
            return [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt}]
            
        return fahrplan

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Zerbst-Daten wurden geladen.")
