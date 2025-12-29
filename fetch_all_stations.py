import requests
import json
import time
from datetime import datetime, timezone

# --- KORRIGIERTE STATIONSLISTE ---
stationen = [
    {"name": "zerbst", "id": "8010393"}, # KORREKTUR: ID für Zerbst/Anhalt
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
    for versuch in range(3):
        # Wir fragen nach Zügen (duration=1200)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=1200&results=20&remarks=true"
        try:
            r = requests.get(url, timeout=25)
            if r.status_code == 200:
                data = r.json()
                departures = data.get('departures', [])
                
                fahrplan = []
                for dep in departures:
                    # OPTIONAL: Busse ausfiltern (Nur Züge wie RE, RB, S-Bahn)
                    typ = dep.get('line', {}).get('product', '')
                    if typ == 'bus': continue 

                    soll_iso = dep.get('plannedWhen')
                    ist_iso = dep.get('when')
                    if not soll_iso: continue
                    
                    soll_zeit = soll_iso.split('T')[1][:5]
                    ist_zeit = ist_iso.split('T')[1][:5] if ist_iso else soll_zeit
                    
                    linie = dep.get('line', {}).get('name', '???').replace(" ", "")
                    
                    info = ""
                    if dep.get('cancelled'):
                        info = "Fällt aus"
                    elif ist_zeit != soll_zeit:
                        info = f"ca. {ist_zeit}"

                    fahrplan.append({
                        "zeit": soll_zeit, 
                        "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                        "linie": linie,
                        "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                        "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                        "info": info
                    })
                
                fahrplan.sort(key=lambda x: x['zeit'])
                return fahrplan
            elif r.status_code == 500:
                time.sleep(5)
                continue
        except Exception as e:
            print(f"Fehler: {e}")
    return []

if __name__ == "__main__":
    for st in stationen:
        print(f"Lade {st['name']} (ID: {st['id']})...")
        daten = hole_daten(st['id'], st['name'])
        with open(f"{st['name']}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
