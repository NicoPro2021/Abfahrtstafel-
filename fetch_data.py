import requests
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")
EVA = "8010386" # Zerbst

def fetch():
    now = datetime.now()
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # Wir lassen 'accept' weg oder setzen es auf XML, das ist stabiler fuer kleine Bahnhoefe
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{EVA}/{d}/{h}"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "accept": "application/xml" 
    }

    print(f"--- XML-CHECK START ---")
    print(f"Anfrage Zerbst: {d}/{h}")

    try:
        r = requests.get(url, headers=headers)
        print(f"DB-Antwort: {r.status_code}")

        if r.status_code == 200:
            # Wir parsen das XML der Bahn
            root = ET.fromstring(r.text)
            fahrplan = []
            
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                if dp is not None and tl is not None:
                    t = dp.get('pt', "")
                    zeit = f"{t[8:10]}:{t[10:12]}" if len(t) >= 12 else "--:--"
                    # Ziel aus dem Pfad (ppth)
                    path = dp.get('ppth', "Ziel")
                    ziel = path.split('|')[-1]
                    
                    fahrplan.append({
                        "zeit": zeit,
                        "linie": tl.get('n', "RB"),
                        "ziel": ziel,
                        "gleis": dp.get('pp', "-")
                    })
            
            if fahrplan:
                fahrplan = sorted(fahrplan, key=lambda x: x['zeit'])[:5]
                with open('daten.json', 'w', encoding='utf-8') as f:
                    json.dump(fahrplan, f, ensure_ascii=False, indent=2)
                print(f"ERFOLG: {len(fahrplan)} Zuege gefunden!")
            else:
                print("HINWEIS: XML erhalten, aber keine Zuege drin.")
        else:
            print(f"FEHLER: {r.status_code} - {r.text[:100]}")

    except Exception as e:
        print(f"FEHLER: {str(e)}")
    print(f"--- DEBUG ENDE ---")

if __name__ == "__main__":
    fetch()
    
