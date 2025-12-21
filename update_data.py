import requests
import json
import os

def get_db_data():
    station_id = "8010405" # Zerbst/Anhalt
    url = f"https://db.transport.rest/stops/{station_id}/departures?duration=120"
    try:
        r = requests.get(url)
        data = r.json()
        abfahrten = []
        for d in data:
            zeit = d['when'][11:16]
            # Nur Züge anzeigen, die heute fahren
            abfahrten.append({
                "zeit": zeit,
                "linie": d['line']['name'],
                "ziel": d['direction'],
                "gleis": d['platform'] if d['platform'] else "--",
                "info": "Zug fällt aus" if d.get('cancelled') else (f"+{int(d['delay']/60)} min" if d.get('delay') and d['delay'] > 60 else "")
            })
        return abfahrten
    except:
        return None

live_data = get_db_data()
if live_in_data:
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(live_data, f, ensure_ascii=False, indent=4)
