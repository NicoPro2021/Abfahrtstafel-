import requests
import json
import os
from datetime import datetime

# Daten aus den GitHub Secrets holen
CLIENT_ID = os.getenv("DB_CLIENT_ID")
CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")
EVA_ZERBST = "8010386"

def fetch_db():
    # Wir holen die aktuellen Fahrplandaten
    now = datetime.now()
    datum = now.strftime("%y%m%d")
    stunde = now.strftime("%H")
    
    # API URL für die aktuelle Stunde in Zerbst
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA_ZERBST}/{datum}/{stunde}"
    
    headers = {
        "DB-Client-Id": CLIENT_ID,
        "DB-Api-Key": CLIENT_SECRET,
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        output = []
        for s in data.get('s', []):
            dp = s.get('dp', {})  # Departure Block
            if dp:
                # Zeit von YYMMDDHHMM zu HH:MM umwandeln
                raw_time = dp.get('pt', "")
                zeit = f"{raw_time[8:10]}:{raw_time[10:12]}" if len(raw_time) >= 12 else "--:--"
                
                # Ziel (letzte Station im Pfad)
                path = dp.get('ppth', "Endstation")
                ziel = path.split('|')[-1]
                
                output.append({
                    "zeit": zeit,
                    "linie": dp.get('l', "RB"),
                    "ziel": ziel,
                    "gleis": dp.get('pp', "-")
                })

        # Nach Zeit sortieren und Top 5 speichern
        output = sorted(output, key=lambda x: x['zeit'])[:5]
        
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("Erfolgreich für Zerbst aktualisiert!")

    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    fetch_db()
    
