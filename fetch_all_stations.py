import requests
import json
import time
from datetime import datetime, timedelta, timezone

# --- STATIONSLISTE (IDs GEPRÜFT) ---
stationen = [
    {"name": "zerbst", "id": "8010390"},
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
    jetzt = datetime.now(timezone.utc)
    # ZWEI VERSCHIEDENE APIS ALS BACKUP
    urls = [
        f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=720&results=20",
        f"https://v6.vbb.transport.rest/stops/{station_id}/departures?duration=720&results=20" # Backup API
    ]
    
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200: continue
            
            data = r.json()
            # Je nach API liegt die Liste in 'departures' oder direkt im Hauptobjekt
            departures = data.get('departures', data if isinstance(data, list) else [])
            
            if not departures or len(departures) == 0:
                continue # Nächste API probieren

            fahrplan = []
            for dep in departures:
                if dep.get('line', {}).get('product') == 'bus': continue

                ist_w = dep.get('when') or dep.get('plannedWhen')
                if not ist_w: continue
                
                zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
                if zug_zeit_obj < (jetzt - timedelta(minutes=2)): continue

                linie = dep.get('line', {}).get('name', '???').replace(" ", "")
                soll_w = dep.get('plannedWhen')
                soll_zeit = soll_w.split('T')[1][:5] if soll_w else ist_w.split('T')[1][:5]
                ist_zeit = ist_w.split('T')[1][:5]
                
                info = "ca. " + ist_zeit if ist_zeit != soll_zeit else ""
                if dep.get('cancelled'): info = "FÄLLT AUS"

                fahrplan.append({
                    "zeit": soll_zeit, 
                    "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                    "linie": linie,
                    "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                    "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                    "info": info
                })

            if fahrplan:
                fahrplan.sort(key=lambda x: x['zeit'])
                return fahrplan[:12]
        except:
            continue
            
    return [] # Wenn beide APIs versagen

if __name__ == "__main__":
    for st in stationen:
        print(f"Update: {st['name']}")
        daten = hole_daten(st['id'], st['name'])
        
        # Falls daten leer sind, prüfen wir, ob wir "Station nicht bedient" erzwingen
        if not daten:
            print(f"WARNUNG: Keine Daten für {st['name']} gefunden.")
        
        filename = f"{st['name']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
