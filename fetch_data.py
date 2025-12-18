import requests
import json

# Die korrekte IBNR fuer Zerbst/Anhalt
STATION_ID = "8010386"
# Die absolut stabilste Schnittstelle (DB-HAFAS via Transport.rest)
URL = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?duration=60&results=5"

def fetch():
    try:
        # User-Agent hilft gegen Blockaden
        headers = {'User-Agent': 'Fahrplan-Display-Project'}
        response = requests.get(URL, headers=headers, timeout=20)
        data = response.json()
        
        fahrplan = []
        # Wir holen die Liste der Abfahrten
        departures = data.get('departures', [])
        
        for d in departures:
            # Zeit von "2024-03-21T12:30:00" auf "12:30" kuerzen
            zeit = d.get('when', '')[11:16] or d.get('plannedWhen', '')[11:16]
            linie = d.get('line', {}).get('name', '---')
            ziel = d.get('direction', 'Ziel unbekannt')
            gleis = d.get('platform', '-')
            
            # Verspaetung in Minuten
            delay = d.get('delay', 0)
            status = f"+{int(delay/60)}" if delay and delay > 0 else "pünktl."
            
            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "status": status
            })
            
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(fahrplan, f, ensure_ascii=False, indent=2)
        print(f"Erfolg! {len(fahrplan)} Züge für Zerbst gefunden.")
        
    except Exception as e:
        print(f"Fehler beim Abrufen: {e}")

if __name__ == "__main__":
    fetch()
