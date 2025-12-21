import requests
import json

# Die interne API-ID für Zerbst/Anhalt (8006663)
API_URL = "https://api.deutschebahn.com/stada/v2/stations/6910" # Beispiel-ID
# Da bahnhof.de oft geschützt ist, nutzen wir eine stabilere Methode:
SEARCH_URL = "https://db-live-abfahrt.herokuapp.com/api/v1/station/Zerbst(Anhalt)"

def get_db_data():
    try:
        # Wir holen die Daten von einem zuverlässigen DB-Daten-Mirror
        response = requests.get(SEARCH_URL, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
        
        abfahrten = []
        # Wir nehmen die ersten 6-8 Einträge
        for train in raw_data['departures'][:8]:
            # Daten für dein ESP32-Format aufbereiten
            abfahrten.append({
                "zeit": train['time'],
                "linie": train['train'],
                "ziel": train['destination'],
                "gleis": train['platform'] if train['platform'] else "--",
                "info": train['delayText'] if train['delayText'] else (train['status'] if train['status'] else "")
            })
        return abfahrten
    except Exception as e:
        print(f"Fehler: {e}")
        return None

# Speichern in die daten.json für GitHub
daten = get_db_data()
if daten:
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
    print("Daten erfolgreich aktualisiert!")
