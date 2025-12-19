import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def fetch():
    # 1. Wir holen die aktuelle Zeit direkt vom Server
    now = datetime.now()
    
    # Wir probieren die aktuelle Stunde UND die nächste Stunde
    # Das fängt Lücken am Stundenübergang ab.
    hours_to_check = [now, now + timedelta(hours=1)]
    
    all_results = []
    
    print(f"--- DYNAMISCHE ABFRAGE START ---")
    
    for check_time in hours_to_check:
        d = check_time.strftime("%y%m%d")
        h = check_time.strftime("%H")
        
        url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
        headers = {
            "DB-Client-Id": ID, 
            "DB-Api-Key": SECRET, 
            "accept": "application/json"
        }
        
        print(f"Prüfe Zeitfenster: {h}:00 Uhr...")
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            data = r.json()
            stops = data.get('s', [])
            for s in stops:
                dp = s.get('dp', {})
                if dp:
                    raw_t = dp.get('pt', "")
                    zeit = f"{raw_t[8:10]}:{raw_t[10:12]}"
                    # Nur Züge nehmen, die nicht in der Vergangenheit liegen
                    if zeit >= now.strftime("%H:%M"):
                        ziel = dp.get('ppth', "Ziel").split('|')[-1]
                        all_results.append({
                            "zeit": zeit,
                            "linie": dp.get('l', "RB"),
                            "ziel": ziel,
                            "gleis": dp.get('pp', "-")
                        })
    
    if all_results:
        # Sortieren nach Uhrzeit und Top 5 speichern
        all_results = sorted(all_results, key=lambda x: x['zeit'])[:5]
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"ERFOLG: {len(all_results)} aktuelle Verbindungen gefunden.")
    else:
        print("KEINE DATEN: Auch für die nächste Stunde gab es keine Treffer.")
    
    print(f"--- ABFRAGE ENDE ---")

if __name__ == "__main__":
    fetch()
