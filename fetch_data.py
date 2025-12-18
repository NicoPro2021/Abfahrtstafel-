import requests
import json

# Deine Zugangsdaten vom DB Portal
CLIENT_ID = "07fd92d1705e4284f3f1533f4bbb9260" 
CLIENT_SECRET = "f3e58426880c7039590ca732abf1ba9f"
EVA_ZERBST = "8010386"

def fetch_db_api():
    # Wir rufen die aktuelle Stunde ab (Beispiel-URL)
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/fchg/{EVA_ZERBST}"
    
    headers = {
        "DB-Client-Id": CLIENT_ID,
        "DB-Api-Key": CLIENT_SECRET,
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        output = []
        # Wir gehen durch die Liste 's' (Stops)
        for stop in data.get('s', []):
            dp = stop.get('dp', {}) # Departure-Block
            if dp:
                # Zeit extrahieren (Format ist YYMMDDHHMM)
                plan_zeit = dp.get('pt', "")[-4:] 
                zeit_formatiert = f"{plan_zeit[:2]}:{plan_zeit[2:]}"
                
                # Ziel extrahieren (Letzte Station im Pfad)
                path = dp.get('ppth', "Unbekannt")
                ziel = path.split('|')[-1]
                
                output.append({
                    "zeit": zeit_formatiert,
                    "linie": dp.get('l', "---"),
                    "ziel": ziel,
                    "gleis": dp.get('pp', "-")
                })
        
        # Sortieren nach Zeit und speichern
        output = sorted(output, key=lambda x: x['zeit'])[:5]
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Fehler bei DB-API: {e}")

if __name__ == "__main__":
    fetch_db_api()
    
