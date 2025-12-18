import requests
import json
import os
from datetime import datetime

# Daten aus den GitHub Secrets laden
CLIENT_ID = os.getenv("DB_CLIENT_ID")
CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")
EVA_ZERBST = "8010386" # Bahnhof Zerbst/Anhalt

def fetch():
    # Aktuelles Datum und Stunde für die DB-API vorbereiten
    now = datetime.now()
    date_str = now.strftime("%y%m%d") # Format: YYMMDD
    hour_str = now.strftime("%H")     # Format: HH
    
    # URL für die Plan-Daten (offizielle Marketplace API)
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA_ZERBST}/{date_str}/{hour_str}"
    
    headers = {
        "DB-Client-Id": CLIENT_ID,
        "DB-Api-Key": CLIENT_SECRET,
        "accept": "application/json" # Zwingt die API, JSON statt XML zu senden
    }

    print(f"Abfrage für Zerbst ({date_str}, {hour_str} Uhr)...")

    try:
        response = requests.get(url, headers=headers)
        print(f"Status-Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            fahrplan = []
            
            # Wir gehen durch alle Stops ('s')
            for s in data.get('s', []):
                dp = s.get('dp', {}) # Abfahrts-Informationen
                if dp:
                    # Zeit formatieren (letzte 4 Ziffern von YYMMDDHHMM)
                    raw_time = dp.get('pt', "")
                    zeit = f"{raw_time[8:10]}:{raw_time[10:12]}" if len(raw_time) >= 12 else "--:--"
                    
                    # Ziel: Wir nehmen das letzte Wort im Pfad (ppth)
                    path = dp.get('ppth', "Ziel unbekannt")
                    ziel = path.split('|')[-1]
                    
                    # Linie (z.B. RE13 oder RB)
                    linie = dp.get('l', "---")
                    
                    fahrplan.append({
                        "zeit": zeit,
                        "linie": linie,
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-"),
                        "status": "pünktl."
                    })
            
            # Sortieren nach Uhrzeit
            fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])
            
            # Datei schreiben
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(fahrplan[:5], f, ensure_ascii=False, indent=2)
            
            print(f"Erfolg! {len(fahrplan)} Abfahrten gespeichert.")
        else:
            print(f"Fehler von der API: {response.text}")

    except Exception as e:
        print(f"Script-Absturz: {e}")

if __name__ == "__main__":
    fetch()
    
