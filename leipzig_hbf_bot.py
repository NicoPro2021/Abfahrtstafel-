import requests, json
from datetime import datetime, timezone

def run():
    # Festgelegte ID für Leipzig Hbf
    url = "https://v6.db.transport.rest/stops/8010205/departures?duration=600&results=20"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            if d.get('line', {}).get('product') in ['bus', 'tram']: continue
            zeit = (d.get('plannedWhen') or d.get('when')).split('T')[1][:5]
            res.append({
                "zeit": zeit, 
                "linie": d['line']['name'], 
                "ziel": d['direction'][:18], 
                "gleis": str(d.get('platform') or "-"),
                "last_web_update": datetime.now(timezone.utc).strftime("%H:%M:%S") # Erzwingt Änderung
            })
        
        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"Leipzig Bot: {len(res)} Züge gespeichert.")
    except Exception as e:
        print(f"Leipzig Bot Fehler: {e}")

if __name__ == "__main__":
    run()
