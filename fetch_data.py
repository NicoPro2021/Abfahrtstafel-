import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def fetch():
    # 1. Server-Zeit auf deutsche Zeit (UTC+1) korrigieren
    # GitHub läuft auf UTC, daher addieren wir 1 Stunde für den Winter
    now_de = datetime.utcnow() + timedelta(hours=1)
    
    # Wir prüfen die aktuelle und die nächsten zwei Stunden
    # So finden wir garantiert die nächsten 5 Abfahrten
    all_results = []
    
    print(f"--- DEUTSCHE ZEIT ABFRAGE START ---")
    print(f"Aktuelle Zeit (DE): {now_de.strftime('%H:%M')} Uhr")
    
    for i in range(3):
        check_time = now_de + timedelta(hours=i)
        d = check_time.strftime("%y%m%d")
        h = check_time.strftime("%H")
        
        url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
        headers = {
            "DB-Client-Id": ID, 
            "DB-Api-Key": SECRET, 
            "accept": "application/json"
        }
        
        print(f"Prüfe Fenster: {h}:00 Uhr...")
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            data = r.json()
            stops = data.get('s', [])
            for s in stops:
                dp = s.get('dp', {})
                if dp:
                    raw_t = dp.get('pt', "")
                    zeit = f"{raw_t[8:10]}:{raw_t[10:12]}"
                    # Nur Züge nehmen, die noch nicht abgefahren sind
                    if zeit >= now_de.strftime("%H:%M"):
                        ziel = dp.get('ppth', "Ziel").split('|')[-1]
                        all_results.append({
                            "zeit": zeit,
                            "linie": dp.get('l', "RB"),
                            "ziel": ziel,
                            "gleis": dp.get('pp', "-")
                        })
        else:
            print(f"Status {r.status_code} für {h}:00 Uhr")

    if all_results:
        # Sortieren und Duplikate/Top 5 filtern
        all_results = sorted(all_results, key=lambda x: x['zeit'])
        # Filtern, um nur einzigartige Zeiten/Ziele zu behalten
        unique_results = []
        seen = set()
        for res in all_results:
            if res['zeit'] not in seen:
                unique_results.append(res)
                seen.add(res['zeit'])
        
        final_data = unique_results[:5]
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print(f"ERFOLG: {len(final_data)} aktuelle Verbindungen gespeichert.")
    else:
        print("KEINE DATEN gefunden. Bitte API-Abonnement prüfen!")
    
    print(f"--- ABFRAGE ENDE ---")

if __name__ == "__main__":
    fetch()
    
