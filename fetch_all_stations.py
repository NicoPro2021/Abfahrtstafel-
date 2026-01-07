import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "Zerbst/Anhalt", 
    "dessau_hbf": "8010077",
    "dessau_sued": "Dessau_Süd",
    "rosslau": "8010297",
    "rodleben": "8010293",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052"
}

def hole_daten(id_oder_name, dateiname):
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'BahnMonitorBot/1.2'}
    
    try:
        final_id = id_oder_name
        if not id_oder_name.isdigit():
            search_url = f"https://v6.db.transport.rest/locations?query={id_oder_name}&results=1"
            search_data = requests.get(search_url, headers=headers, timeout=10).json()
            if search_data:
                final_id = search_data[0]['id']
            else: return None

        url = f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&results=50"
        r = requests.get(url, headers=headers, timeout=15).json()
        
        departures = r.get('departures', [])
        if not departures:
            print(f"(!) Keine neuen Daten für {dateiname}, überspringe Speichern.")
            return None # Gibt None zurück, wenn die API leer ist

        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress'] and "Bus" not in line.get('name', ''):
                    continue

                res.append({
                    "zeit": datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00')).strftime("%H:%M"), 
                    "echte_zeit": datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')).strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{int((datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')) - datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))).total_seconds() / 60)}" if int((datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')) - datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))).total_seconds() / 60) > 0 else ""), 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
        return res
    except:
        return None

if __name__ == "__main__":
    for dateiname, identifier in STATIONS.items():
        print(f"Check {dateiname}...")
        daten = hole_daten(identifier, dateiname)
        
        # WICHTIG: Nur speichern, wenn wir echte Daten bekommen haben!
        if daten is not None and len(daten) > 0:
            with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            print(f"-> {dateiname}.json aktualisiert.")
        
        time.sleep(2)
