import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def get_timetable(date_str, hour_str):
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{date_str}/{hour_str}"
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }
    return requests.get(url, headers=headers)

def fetch():
    now = datetime.now()
    # Wir versuchen es zuerst mit der aktuellen Stunde
    d1, h1 = now.strftime("%y%m%d"), now.strftime("%H")
    # Und als Backup die nächste Stunde
    next_hour = now + timedelta(hours=1)
    d2, h2 = next_hour.strftime("%y%m%d"), next_hour.strftime("%H")

    print(f"--- DEBUG START ---")
    
    # Versuch 1
    print(f"Versuch 1: {d1} um {h1}:00 Uhr")
    res = get_timetable(d1, h1)
    
    # Falls 404, probiere Versuch 2
    if res.status_code != 200:
        print(f"Status {res.status_code}. Probiere Backup: {d2} um {h2}:00 Uhr")
        res = get_timetable(d2, h2)

    print(f"Finale Antwort: {res.status_code}")

    if res.status_code == 200:
        data = res.json()
        stops = data.get('s', [])
        fahrplan = []
        
        for s in stops:
            dp = s.get('dp', {})
            if dp:
                t = dp.get('pt', "")
                zeit = f"{t[8:10]}:{t[10:12]}" if len(t) >= 12 else "--:--"
                ziel = dp.get('ppth', "Ziel").split('|')[-1]
                fahrplan.append({"zeit": zeit, "linie": dp.get('l', "RB"), "ziel": ziel, "gleis": dp.get('pp', "-")})
        
        if fahrplan:
            fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])[:5]
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(fahrplan, f, ensure_ascii=False, indent=2)
            print(f"ERFOLG: {len(fahrplan)} Züge gespeichert.")
        else:
            print("KEINE DATEN in der Antwort gefunden.")
    else:
        print(f"FEHLER: DB API liefert immer noch {res.status_code}")
    
    print(f"--- DEBUG ENDE ---")

if __name__ == "__main__":
    fetch()
    
