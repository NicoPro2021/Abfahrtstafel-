import requests
import json
from datetime import datetime, timezone

# --- STATIONSLISTE ---
stationen = [
    {"name": "zerbst", "id": "8013313"},
    {"name": "rodleben", "id": "8012808"},
    {"name": "rosslau", "id": "8010298"},
    {"name": "dessau_hbf", "id": "8010077"},
    {"name": "dessau_sued", "id": "8011384"},
    {"name": "magdeburg_hbf", "id": "8010224"},
    {"name": "magdeburg_neustadt", "id": "8010226"},
    {"name": "magdeburg_herrenkrug", "id": "8011910"},
    {"name": "leipzig_hbf", "id": "8010205"}
]

def hole_daten(station_id, station_name):
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=1200&results=20"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when') or dep.get('plannedWhen')
            if not ist_w: continue
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_zeit = ist_w.split('T')[1][:5]
            
            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": "", 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                "gleis": str(dep.get('platform') or "-"),
                "info": ""
            })

        # --- FALLBACK: Wenn die API leer zurückgibt, schreibe Test-Info ---
        if not fahrplan:
            return [{
                "zeit": "--:--", 
                "echte_zeit": "", 
                "linie": "INFO", 
                "ziel": "API liefert keine Daten", 
                "gleis": "!", 
                "info": "Bitte ID prüfen"
            }]

        return fahrplan[:12]

    except Exception as e:
        return [{
            "zeit": "ERR", 
            "echte_zeit": "", 
            "linie": "FAIL", 
            "ziel": str(e)[:20], 
            "gleis": "!", 
            "info": "Verbindungsfehler"
        }]

if __name__ == "__main__":
    for st in stationen:
        daten = hole_daten(st['id'], st['name'])
        filename = f"{st['name']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Datei {filename} geschrieben.")
