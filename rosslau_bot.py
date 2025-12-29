import requests, json
from datetime import datetime, timedelta, timezone
def hole_daten():
    try:
        suche = requests.get("https://v6.db.transport.rest/locations?query=Roßlau(Elbe)&results=1", timeout=10).json()
        r = requests.get(f"https://v6.db.transport.rest/stops/{suche[0]['id']}/departures?duration=480&results=10", timeout=15).json()
        return [{"zeit": (d.get('plannedWhen') or d['when']).split('T')[1][:5], "linie": d['line']['name'], "ziel": d['direction'][:18], "gleis": str(d.get('platform') or "-"), "info": ""} for d in r.get('departures', [])]
    except: return []
if __name__ == "__main__":
    with open('rosslau.json', 'w', encoding='utf-8') as f: json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
