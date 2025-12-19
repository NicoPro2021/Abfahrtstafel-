import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def fetch():
    # Zeitkorrektur auf Deutschland (UTC+1)
    now_de = datetime.utcnow() + timedelta(hours=1)
    all_results = []
    
    print(f"--- API-DIAGNOSE START ---")
    print(f"Zeit (DE): {now_de.strftime('%H:%M')} | Station: {EVA}")
    
    # Wir prüfen die aktuelle und die nächsten zwei Stunden
    for i in range(3):
        check_time = now_de + timedelta(hours=i)
        d = check_time.strftime("%y%m%d")
        h = check_time.strftime("%H")
        
        # Versuche v2 der API (oft zuverlässiger bei 404-Problemen)
        url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
        
        headers = {
            "DB-Client-Id": ID,
            "DB-Api-Key": SECRET,
            "User-Agent": "FahrplanBot/1.0",
            "Accept": "application/json"
        }
        
        try:
            r = requests.get(url, headers=headers)
            print(f"Stunde {h}:00 -> Status {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                for s in data.get('s', []):
                    dp = s.get('dp', {})
                    if dp:
                        t = dp.get('pt', "")
                        zeit = f"{t[8:10]}:{t[10:12]}"
                        if zeit >= now_de.strftime("%H:%M") or i > 0:
                            ziel = dp.get('ppth', "Ziel").split('|')[-1]
                            all_results.append({
                                "zeit": zeit,
                                "linie": dp.get('l', "RB"),
                                "ziel": ziel,
                                "gleis": dp.get('pp', "-")
                            })
            elif r.status_code == 401:
                print("FEHLER: Keys ungültig (Unauthorized).")
            elif r.status_code == 403:
                print("FEHLER: Abo nicht aktiv (Forbidden).")
        except Exception as e:
            print(f"Verbindungsfehler: {str(e)}")

    if all_results:
        all_results = sorted(all_results, key=lambda x: x['zeit'])
        # Duplikate entfernen
        final = []
        seen = set()
        for res in all_results:
            if res['zeit'] not in seen:
                final.append(res)
                seen.add(res['zeit'])
        
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(final[:5], f, ensure_ascii=False, indent=2)
        print(f"ERFOLG: {len(final[:5])} Züge gespeichert.")
    else:
        print("KEINE DATEN: Bitte prüfen, ob die 'Timetables' API im DB-Portal WIRKLICH dieser Client-ID zugewiesen ist.")

if __name__ == "__main__":
    fetch()
    
