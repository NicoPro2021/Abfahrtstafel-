import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")

def get_timetable(eva, name):
    # Deutsche Zeit berechnen (UTC+1)
    now_de = datetime.utcnow() + timedelta(hours=1)
    d, h = now_de.strftime("%y%m%d"), now_de.strftime("%H")
    
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{eva}/{d}/{h}"
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "Accept": "application/json"
    }
    
    print(f"Versuche {name} ({eva}) für {h}:00 Uhr...")
    return requests.get(url, headers=headers)

def fetch():
    print("--- NEUE KEYS TEST-LAUF ---")
    
    # 1. Test Zerbst
    res = get_timetable("8010386", "Zerbst")
    
    # 2. Falls Zerbst 404 liefert, Test Berlin zur Diagnose
    if res.status_code != 200:
        print(f"Zerbst Status: {res.status_code}. Teste Referenz Berlin...")
        res = get_timetable("8011160", "Berlin Hbf")

    if res.status_code == 200:
        data = res.json()
        stops = []
        for s in data.get('s', []):
            dp = s.get('dp', {})
            if dp:
                t = dp.get('pt', "")
                stops.append({
                    "zeit": f"{t[8:10]}:{t[10:12]}",
                    "linie": dp.get('l', "RB"),
                    "ziel": dp.get('ppth', "Ziel").split('|')[-1],
                    "gleis": dp.get('pp', "-")
                })
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(stops[:5], f, ensure_ascii=False, indent=2)
        print(f"ERFOLG: Daten wurden mit Status 200 empfangen!")
    else:
        print(f"FEHLER: Auch mit neuen Keys Status {res.status_code}. Bitte API-Abo im Portal prüfen!")

if __name__ == "__main__":
    fetch()
    
