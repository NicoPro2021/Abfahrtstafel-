import requests
import json
import os
from datetime import datetime

# Deine Zugangsdaten aus den GitHub Secrets
CLIENT_ID = os.getenv("DB_CLIENT_ID")
CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")
# Die EVA-Nummer fuer Zerbst/Anhalt
EVA_ZERBST = "8010386"

def fetch():
    now = datetime.now()
    # Die API erwartet das Datum im Format YYMMDD und die Stunde HH
    datum = now.strftime("%y%m%d")
    stunde = now.strftime("%H")
    
    # URL fuer die Fahrplandaten (Planungs-Daten)
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA_ZERBST}/{datum}/{stunde}"
    
    headers = {
        "DB-Client-Id": CLIENT_ID,
        "DB-Api-Key": CLIENT_SECRET,
        "accept": "application/json" # Wir erzwingen JSON, um XML-Fehler zu vermeiden
    }

    print(f"Abfrage fuer Zerbst: {datum} um {stunde} Uhr")

    try:
        response = requests.get(url, headers=headers)
        print(f"Status-Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            fahrplan = []
            
            # Die DB liefert Stops ('s') mit Abfahrten ('dp')
            for s in data.get('s', []):
                dp = s.get('dp', {})
                if dp:
                    # Zeit von YYMMDDHHMM zu HH:MM umwandeln
                    raw_time = dp.get('pt', "")
                    zeit = f"{raw_time[8:10]}:{raw_time[10:12]}" if len(raw_time) >= 12 else "--:--"
                    
                    # Das Ziel ist die letzte Station in der Pfad-Liste (ppth)
                    path = dp.get('ppth', "Endstation")
                    ziel = path.split('|')[-1]
                    
                    fahrplan.append({
                        "zeit": zeit,
                        "linie": dp.get('l', "RB"),
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })

            # Nach Uhrzeit sortieren und Top 5 nehmen
            fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])[:5]
            
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(fahrplan, f, ensure_ascii=False, indent=2)
            
            print(f"Erfolg: {len(fahrplan)} Züge in daten.json gespeichert.")
        else:
            print(f"Fehler: API antwortet mit {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Script-Fehler: {e}")

if __name__ == "__main__":
    fetch()
            
