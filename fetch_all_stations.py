import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

# Zerbst als Name, um Zinnowitz (Usedom) zu vermeiden
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "Zerbst/Anhalt", 
    "dessau_hbf": "8010077",
    "dessau_sued": "8011382",
    "rosslau": "8010297",
    "rodleben": "8010293",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052"
}

def hole_daten(identifier, dateiname):
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'BahnMonitor/5.0'}
    try:
        final_id = identifier
        if not identifier.isdigit():
            s_data = requests.get(f"https://v6.db.transport.rest/locations?query={identifier}&results=1", timeout=10).json()
            final_id = s_data[0]['id'] if s_data else None
        
        if not final_id: return None

        r = requests.get(f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180", timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        # Wir fügen IMMER ein Update-Feld hinzu, damit die Datei sich IMMER ändert!
        res.append({"last_update": u_zeit, "station": dateiname})

        for d in departures:
            try:
                line = d.get('line', {})
                planned = datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))
                actual = datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00'))
                diff = int((actual - planned).total_seconds() / 60)
                res.append({
                    "zeit": planned.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else "")
                })
            except: continue
        return res
    except: return None

if __name__ == "__main__":
    # Wir holen uns den Pfad, wo das Skript liegt
    base_path = os.path.dirname(os.path.abspath(__file__))
    for dateiname, identifier in STATIONS.items():
        daten = hole_daten(identifier, dateiname)
        if daten:
            file_path = os.path.join(base_path, f"{dateiname}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            print(f"Datei geschrieben: {file_path}")
