import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def fetch():
    # Wir nehmen die aktuelle Stunde
    now = datetime.now()
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # TEST: Wir versuchen es mit der offiziellen Timetable-API
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }

    print(f"--- DEBUG START ---")
    print(f"Versuche Zerbst: {d} um {h}:00 Uhr")
    
    try:
        r = requests.get(url, headers=headers)
        print(f"Status von DB: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            # Die Struktur der Antwort kann je nach API-Version variieren
            stops = data.get('s', [])
            
            abfahrten = []
            for s in stops:
                dp = s.get('dp', {})
                if dp:
                    raw_t = dp.get('pt', "")
                    zeit = f"{raw_t[8:10]}:{raw_t[10:12]}" if len(raw_t) >= 12 else "--:--"
                    
                    # Extrahiere die Linie (z.B. RB13)
                    tl = s.get('tl', {})
                    linie = tl.get('n', "RB")
                    
                    # Ziel extrahieren
                    path = dp.get('ppth', "Ziel")
                    ziel = path.split('|')[-1]
                    
                    abfahrten.append({
                        "zeit": zeit,
                        "linie": linie,
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })
            
            if abfahrten:
                abfahrten = sorted(abfahrten, key=lambda x: x['zeit'])[:5]
                with open('daten.json', 'w', encoding='utf-8') as f:
                    json.dump(abfahrten, f, ensure_ascii=False, indent=2)
                print(f"ERFOLG: {len(abfahrten)} Zuege gespeichert!")
            else:
                print("KEINE DATEN: API lieferte leere Liste.")
        else:
            print(f"FEHLER: API sagt {r.status_code}")
            # Falls 404 kommt, probieren wir in 15 Min die nächste Stunde
            
    except Exception as e:
        print(f"ABSTURZ: {str(e)}")
    print(f"--- DEBUG ENDE ---")

if __name__ == "__main__":
    fetch()
    
