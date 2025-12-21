import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Zerbst/Anhalt ID
STATION_ID = "8006654"
# Die stabilste öffentliche Schnittstelle
URL = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?duration=120&results=6"

def hole_daten():
    try:
        # Wir fragen die API ab
        response = requests.get(URL, timeout=15)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # Die Daten liegen bei dieser API im Feld 'departures'
        departures = data.get('departures', [])
        
        fahrplan = []

        for dep in departures:
            # Zeit extrahieren (Format: 2023-12-21T16:30:00+01:00)
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw else "--:--"
            
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???')
            
            # Ziel
            ziel = dep.get('direction', 'Unbekannt')
            
            # Gleis
            gleis = dep.get('platform') or "-"
            
            # Verspätung in Minuten
            delay = dep.get('delay')
            info = ""
            if delay is not None:
                info = f"+{int(delay/60)}" if delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": str(gleis),
                "info": info
            })

        if not fahrplan:
            return [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": ""}]
            
        return fahrplan

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Fertig!")
