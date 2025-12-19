import requests
import json
import os
from datetime import datetime

# Hole Keys aus den Secrets
ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst/Anhalt

def fetch():
    # Wir nehmen die aktuelle Zeit (UTC/GMT ist oft sicherer bei APIs)
    now = datetime.now()
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # Offizielle URL fuer Fahrplandaten
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }

    print(f"--- DEBUG START ---")
    print(f"Anfrage fuer: {d} um {h}:00 Uhr")
    
    try:
        r = requests.get(url, headers=headers)
        print(f"Status von DB: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            # Wir holen die Liste der Halte ('s')
            stops = data.get('timetable', {}).get('s', []) if 'timetable' in data else data.get('s', [])
            
            abfahrten = []
            for s in stops:
                dp = s.get('dp', {})
                if dp:
                    raw_t = dp.get('pt', "")
                    zeit = f"{raw_t[8:10]}:{raw_t[10:12]}" if len(raw_t) >= 12 else "--:--"
                    # Den Zielbahnhof aus dem Pfad extrahieren
                    ziel = dp.get('ppth', "Endstation").split('|')[-1]
                    
                    abfahrten.append({
                        "zeit": zeit,
                        "linie": dp.get('l', "RB"),
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })
            
            # Nur speichern, wenn wir wirklich Zuege gefunden haben
            if abfahrten:
                abfahrten = sorted(abfahrten, key=lambda x: x['zeit'])[:5]
                with open('daten.json', 'w', encoding='utf-8') as f:
                    json.dump(abfahrten, f, ensure_ascii=False, indent=2)
                print(f"ERFOLG: {len(abfahrten)} Zuege gespeichert.")
            else:
                print("HINWEIS: Keine Zuege in dieser Stunde gefunden.")
                
        else:
            print(f"FEHLER: API antwortet mit {r.status_code}")
            print(f"Antwort: {r.text}")

    except Exception as e:
        print(f"ABSTURZ: {str(e)}")
    print(f"--- DEBUG ENDE ---")

if __name__ == "__main__":
    fetch()
    
