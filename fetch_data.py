import requests
import json
import os
from datetime import datetime

# Diese Werte muessen in deinen GitHub Secrets stehen!
ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst/Anhalt

def fetch():
    now = datetime.now()
    datum = now.strftime("%y%m%d")
    stunde = now.strftime("%H")
    
    # URL fuer die offizielle Timetables API
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{datum}/{stunde}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }

    print(f"--- START LAUF ---")
    print(f"Bahnhof: {EVA} | Zeit: {datum} {stunde}:00")

    try:
        r = requests.get(url, headers=headers)
        print(f"Antwort-Status: {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            stops = data.get('s', [])
            fahrplan = []
            
            for s in stops:
                dp = s.get('dp', {}) # Departure-Daten
                if dp:
                    raw_zeit = dp.get('pt', "")
                    zeit_formatiert = f"{raw_zeit[8:10]}:{raw_zeit[10:12]}" if len(raw_zeit) >= 12 else "--:--"
                    
                    # Ziel aus dem ppth-String (letztes Element)
                    ziel = dp.get('ppth', "Ziel").split('|')[-1]
                    
                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": dp.get('l', "RB"),
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })

            # Sortieren und die nächsten 5 Abfahrten speichern
            fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])[:5]
            
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(fahrplan, f, ensure_ascii=False, indent=2)
            
            print(f"ERFOLG: {len(fahrplan)} Züge in daten.json geschrieben.")
        
        elif r.status_code == 404:
            print("INFO: Aktuell keine Plandaten für diese Stunde vorhanden.")
        else:
            print(f"API-FEHLER: {r.status_code}")
            print(r.text)

    except Exception as e:
        print(f"SCRIPT-FEHLER: {str(e)}")

if __name__ == "__main__":
    fetch()
    
