import requests
import json
import os
from datetime import datetime

# Daten aus den GitHub Secrets laden
CLIENT_ID = os.getenv("DB_CLIENT_ID")
CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")
EVA_ZERBST = "8010386" # Bahnhof Zerbst/Anhalt

def fetch_db_data():
    now = datetime.now()
    datum = now.strftime("%y%m%d")
    stunde = now.strftime("%H")
    
    # Offizielle DB API URL für den Fahrplan (Plan-Daten)
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA_ZERBST}/{datum}/{stunde}"
    
    headers = {
        "DB-Client-Id": CLIENT_ID,
        "DB-Api-Key": CLIENT_SECRET,
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        # Falls die API XML statt JSON liefert, fangen wir das hier ab
        # Wir gehen aber davon aus, dass deine API-Einstellung JSON erlaubt
        data = response.json()
        
        fahrplan = []
        # Wir suchen im "s" (Stops) Feld nach "dp" (Departure/Abfahrt)
        for stop in data.get('s', []):
            dp = stop.get('dp', {})
            if dp:
                # Zeit von YYMMDDHHMM zu HH:MM kürzen
                raw_time = dp.get('pt', "")
                zeit = f"{raw_time[8:10]}:{raw_time[10:12]}" if len(raw_time) >= 12 else "--:--"
                
                # Ziel aus dem Pfad (letztes Element)
                path = dp.get('ppth', "Endstation")
                ziel = path.split('|')[-1]
                
                fahrplan.append({
                    "zeit": zeit,
                    "linie": dp.get('l', "RB"),
                    "ziel": ziel,
                    "gleis": dp.get('pp', "-"),
                    "status": "pünktl."
                })

        # Sortieren nach Zeit und Top 5 speichern
        fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])[:5]
        
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(fahrplan, f, ensure_ascii=False, indent=2)
            
        print(f"Update erfolgreich! {len(fahrplan)} Züge gefunden.")

    except Exception as e:
        print(f"Fehler beim Abruf: {e}")

if __name__ == "__main__":
    fetch_db_data()
    
