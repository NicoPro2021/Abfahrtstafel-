import requests
import json
import os
from datetime import datetime

# Wir holen die Keys direkt aus den GitHub Secrets
ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst/Anhalt

def fetch():
    now = datetime.now()
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/json"
    }

    print(f"--- DEBUG START ---")
    print(f"Zeitpunkt: {d} um {h}:00 Uhr")
    
    if not ID or not SECRET:
        print("KRITISCH: ID oder SECRET sind leer! Prüfe GitHub Secrets.")
        return

    try:
        r = requests.get(url, headers=headers)
        print(f"Status von DB: {r.status_code}") # Hier steht die Wahrheit!
        
        if r.status_code == 200:
            data = r.json()
            abfahrten = []
            
            for s in data.get('s', []):
                dp = s.get('dp', {})
                if dp:
                    # Zeit & Ziel extrahieren
                    raw_t = dp.get('pt', "")
                    zeit = f"{raw_t[8:10]}:{raw_t[10:12]}" if len(raw_t) >= 12 else "--:--"
                    ziel = dp.get('ppth', "Ziel").split('|')[-1]
                    
                    abfahrten.append({
                        "zeit": zeit,
                        "linie": dp.get('l', "RB"),
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })
            
            # Immer speichern, damit die Datei nicht leer bleibt
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(abfahrten[:5], f, ensure_ascii=False, indent=2)
            
            print(f"ERFOLG: {len(abfahrten)} Züge gefunden und gespeichert.")
            
        elif r.status_code == 401:
            print("FEHLER 401: Deine API-Keys sind falsch oder ungültig!")
        else:
            print(f"FEHLER {r.status_code}: {r.text}")

    except Exception as e:
        print(f"SCRIPT-ABSTURZ: {str(e)}")
    print(f"--- DEBUG ENDE ---")

if __name__ == "__main__":
    fetch()
