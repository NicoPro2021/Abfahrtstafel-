import requests
import json
import os
from datetime import datetime

# Hole Keys aus den Secrets
ID = os.getenv("DB_CLIENT_ID")
KEY = os.getenv("DB_CLIENT_SECRET")
STATION = "8010386" # Zerbst

def start():
    now = datetime.now()
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # Offizielle Marketplace API
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{STATION}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": KEY,
        "accept": "application/json"
    }

    print(f"Versuche Abfrage: {d} um {h} Uhr")
    
    try:
        r = requests.get(url, headers=headers)
        print(f"API-Status: {r.status_code}") # Wenn hier nicht 200 steht, liegt es an den Keys!
        
        if r.status_code == 200:
            data = r.json()
            results = []
            for s in data.get('s', []):
                dp = s.get('dp', {})
                if dp:
                    t = dp.get('pt', "")
                    zeit = f"{t[8:10]}:{t[10:12]}" if len(t) >= 12 else "--:--"
                    ziel = dp.get('ppth', "Ziel").split('|')[-1]
                    results.append({"zeit": zeit, "linie": dp.get('l', "RB"), "ziel": ziel, "gleis": dp.get('pp', "-")})
            
            # SORTIEREN UND SPEICHERN
            results = sorted(results, key=lambda x: x['zeit'])[:5]
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"DATEI GESCHRIEBEN: {len(results)} Züge.")
        else:
            print(f"API FEHLER TEXT: {r.text}")
            
    except Exception as e:
        print(f"ABSTURZ: {str(e)}")

if __name__ == "__main__":
    start()
    
