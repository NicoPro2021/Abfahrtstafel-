import requests
import json
import time
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
    # Wir versuchen es bis zu 3 Mal, falls der Server (500) spinnt
    for versuch in range(3):
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=1200&results=15"
        try:
            r = requests.get(url, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                departures = data.get('departures', [])
                
                if not departures:
                    return [] # Station hat aktuell einfach keine Fahrten

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
                return fahrplan
            
            elif r.status_code == 500:
                print(f"Server-Fehler (500) bei {station_name}, Versuch {versuch+1}...")
                time.sleep(5) # 5 Sekunden warten vor Neustart
                continue
                
        except Exception as e:
            print(f"Fehler: {e}")
            
    # Wenn alle Versuche scheitern:
    return []

if __name__ == "__main__":
    for st in stationen:
        print(f"Lade {st['name']}...")
        daten = hole_daten(st['id'], st['name'])
        
        # WICHTIG: Erzeugt die Datei immer. Wenn daten=[], wird die Seite 'nicht bedient' zeigen.
        with open(f"{st['name']}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
