import requests
import json

# ID für Zerbst/Anhalt
STATION_ID = "8010386"
URL = f"https://db-abfahrt.vve.workers.dev/?station={STATION_ID}"

def fetch_and_save():
    try:
        response = requests.get(URL, timeout=10)
        data = response.json()
        
        fahrplan = []
        # Wir nehmen die nächsten 6 Züge
        for zug in data[:6]:
            fahrplan.append({
                "zeit": zug.get("zeit", ""),
                "linie": zug.get("linie", ""),
                "ziel": zug.get("ziel", ""),
                "gleis": zug.get("gleis", ""),
                "status": zug.get("status", "") # Hier kommt die Verspätung rein
            })
            
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(fahrplan, f, ensure_ascii=False, indent=2)
        print("Daten für Zerbst aktualisiert!")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    fetch_and_save()
