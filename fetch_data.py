import requests
import json
import os
from datetime import datetime

# Hole die AKTUELLEN Keys aus den Secrets
ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst/Anhalt

def fetch():
    now = datetime.now()
    # Das Format MUSS exakt YYMMDD und HH sein
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # Offizielle Marketplace URL
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }

    print(f"--- START ---")
    print(f"Abfrage fuer Zerbst: {d} um {h}:00 Uhr")

    try:
        r = requests.get(url, headers=headers)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            stops = data.get('s', [])
            results = []
            for s in stops:
                dp = s.get('dp', {})
                if dp:
                    t = dp.get('pt', "")
                    zeit = f"{t[8:10]}:{t[10:12]}" if len(t) >= 12 else "--:--"
                    ziel = dp.get('ppth', "Ziel").split('|')[-1]
                    results.append({"zeit": zeit, "linie": dp.get('l', "RB"), "ziel": ziel, "gleis": dp.get('pp', "-")})
            
            results = sorted(results, key=lambda x: x['zeit'])[:5]
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"GESPEICHERT: {len(results)} Zuege.")
        else:
            print(f"FEHLER TEXT: {r.text}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    fetch()
    
