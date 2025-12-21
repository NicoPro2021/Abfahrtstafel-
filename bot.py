import requests
import json

# URL zur stabilen Datenquelle für Zerbst
URL = "https://db-live-abfahrt.herokuapp.com/api/v1/station/Zerbst(Anhalt)"

def hole_daten():
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()
        daten = response.json()
        
        ergebnis = []
        # Wir nehmen die nächsten 8 Abfahrten
        for zug in daten['departures'][:8]:
            # Das Format, das dein ESP32 und HTML brauchen
            ergebnis.append({
                "zeit": zug['time'],
                "linie": zug['train'],
                "ziel": zug['destination'],
                "gleis": zug['platform'] if zug['platform'] else "--",
                "info": zug['delayText'] if zug['delayText'] else (zug['status'] if zug['status'] else "")
            })
        return ergebnis
    except Exception as e:
        print(f"Fehler: {e}")
        return None

# Speichern
neue_daten = hole_daten()
if neue_daten:
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(neue_daten, f, ensure_ascii=False, indent=4)
    print("Update erfolgreich!")
