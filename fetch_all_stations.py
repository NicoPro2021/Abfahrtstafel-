import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

# Konfiguration der Bahnhöfe
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
    headers = {'User-Agent': 'BahnMonitorBot/1.3'}
    
    try:
        # ID Auflösung (besonders für Zerbst wichtig)
        final_id = id_oder_name
        if not id_oder_name.isdigit():
            search_url = f"https://v6.db.transport.rest/locations?query={id_oder_name}&results=1"
            search_data = requests.get(search_url, headers=headers, timeout=10).json()
            if search_data:
                final_id = search_data[0]['id']
            else: return None

        # Abfrage
        url = f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&results=50"
        r = requests.get(url, headers=headers, timeout=15).json()
        
        departures = r.get('departures', [])
        if not departures:
            return None # API hat keine Daten geliefert

        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Filter: Nur Züge und SEV
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress'] and "Bus" not in line.get('name', ''):
                    continue

                planned = datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))
                actual = datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00'))
                diff = int((actual - planned).total_seconds() / 60)
                
                res.append({
                    "zeit": planned.strftime("%H:%M"), 
                    "echte_zeit": actual.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else ""), 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
        return res
    except:
        return None

if __name__ == "__main__":
    for dateiname, identifier in STATIONS.items():
        print(f"Abfrage {dateiname}...")
        daten = hole_daten(identifier, dateiname)
        
        # NUR SPEICHERN WENN DATEN DA SIND (verhindert [])
        if daten is not None and len(daten) > 0:
            with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            print(f"Erfolg: {dateiname}.json gespeichert.")
        else:
            print(f"Übersprungen: {dateiname} lieferte keine Daten.")
        
        time.sleep(2) # Kurze Pause zwischen Abfragen
