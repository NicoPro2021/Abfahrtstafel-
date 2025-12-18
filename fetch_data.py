import requests
import json

# Die korrekte IBNR fuer Zerbst/Anhalt
STATION_ID = "8010386"
URL = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?duration=60&results=5"

def fetch():
    try:
        response = requests.get(URL, timeout=20)
        data = response.json()
        fahrplan = []
        departures = data.get('departures', [])
        
        for d in departures:
            zeit = (d.get('when') or d.get('plannedWhen') or "00:00:00")[11:16]
            linie = d.get('line', {}).get('name', '---')
            ziel = d.get('direction', 'Ziel unbekannt')
            gleis = d.get('platform', '-')
            delay = d.get('delay', 0)
            status = f"+{int(delay/60)}" if delay and delay > 0 else "pünktl."
            
            fahrplan.append({"zeit": zeit, "linie": linie, "ziel": ziel, "gleis": gleis, "status": status})
            
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(fahrplan, f, ensure_ascii=False, indent=2)
        print("Erfolg!")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    fetch()
    
