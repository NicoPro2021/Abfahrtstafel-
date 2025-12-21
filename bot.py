import requests
import json
import time

# URL für Zerbst/Anhalt
URL = "https://db-live-abfahrt.herokuapp.com/api/v1/station/Zerbst(Anhalt)"

def hole_daten():
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()
        daten = response.json()
        ergebnis = []
        for zug in daten['departures'][:8]:
            ergebnis.append({
                "zeit": zug['time'],
                "linie": zug['train'],
                "ziel": zug['destination'],
                "gleis": zug['platform'] if zug['platform'] else "--",
                "info": zug['delayText'] if zug['delayText'] else (zug['status'] if zug['status'] else "")
            })
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(ergebnis, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Fehler: {e}")
        return False

# Der Bot aktualisiert 4 Minuten lang alle 30 Sek, dann beendet er sich
start_zeit = time.time()
while time.time() - start_zeit < 240: 
    if hole_daten():
        print("Daten-Update erfolgreich...")
    time.sleep(30)
