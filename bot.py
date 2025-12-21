import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATION_ID = "8006654"
URL = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?results=6&duration=120"

def hole_daten():
    try:
        response = requests.get(URL, timeout=15)
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        # Zeitstempel für das Update hinzufügen
        jetzt = datetime.now().strftime("%H:%M:%S")

        for dep in departures:
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw else "--:--"
            linie = dep.get('line', {}).get('name', '???')
            ziel = dep.get('direction', 'Unbekannt')
            gleis = dep.get('platform') or "-"
            
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": str(gleis),
                "info": info,
                "update": jetzt  # Hier steht die letzte Aktualisierung
            })

        return fahrplan if fahrplan else [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Zerbst-Daten inklusive Zeitstempel aktualisiert!")
