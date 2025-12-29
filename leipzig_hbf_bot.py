import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    try:
        # Suche nach Leipzig Hbf
        suche = requests.get("https://v6.db.transport.rest/locations?query=Leipzig Hbf&results=1", timeout=10).json()
        # Abfrage der Abfahrten
        r = requests.get(f"https://v6.db.transport.rest/stops/{suche[0]['id']}/departures?duration=480&results=15", timeout=15).json()
        
        res = []
        for d in r.get('departures', []):
            # Filter für Züge (keine Busse/Straßenbahnen)
            if d.get('line', {}).get('product') in ['bus', 'tram']: continue
            
            zeit = (d.get('plannedWhen') or d['when']).split('T')[1][:5]
            res.append({
                "zeit": zeit, 
                "linie": d['line']['name'], 
                "ziel": d['direction'][:18], 
                "gleis": str(d.get('platform') or "-"), 
                "info": ""
            })
        return res
    except: 
        return []

if __name__ == "__main__":
    # Hier wird der Dateiname festgelegt
    with open('leipzig_hbf.json', 'w', encoding='utf-8') as f: 
        json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
