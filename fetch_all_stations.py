import requests
import json
import time
from datetime import datetime, timezone

# --- STATIONSLISTE (KORRIGIERT 2025) ---
stationen = [
    {"name": "zerbst", "id": "8010392"},           # Zerbst/Anhalt (Magdeburg-Dessau)
    {"name": "rodleben", "id": "8012808"},         # Rodleben
    {"name": "rosslau", "id": "8010298"},          # Roßlau (Elbe)
    {"name": "dessau_hbf", "id": "8010077"},       # Dessau Hbf
    {"name": "dessau_sued", "id": "8011384"},      # Dessau Süd
    {"name": "magdeburg_hbf", "id": "8010224"},    # Magdeburg Hbf
    {"name": "magdeburg_neustadt", "id": "8010226"},
    {"name": "magdeburg_herrenkrug", "id": "8011910"},
    {"name": "leipzig_hbf", "id": "8010205"}
]

def hole_daten(station_id, station_name):
    # Retry-Logik: Bis zu 3 Versuche bei Server-Fehlern
    for versuch in range(3):
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=1200&results=20&remarks=true"
        try:
            r = requests.get(url, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                departures = data.get('departures', [])
                
                if not departures:
                    return []

                fahrplan = []
                for dep in departures:
                    # Busse ausfiltern, falls gewuenscht (optional)
                    if dep.get('line', {}).get('product') == 'bus':
                        continue

                    # Soll-Zeit und Ist-Zeit abgreifen
                    soll_iso = dep.get('plannedWhen')
                    ist_iso = dep.get('when')
                    
                    if not soll_iso: continue
                    
                    # Zeit-Formatierung HH:MM
                    soll_zeit = soll_iso.split('T')[1][:5]
                    ist_zeit = ist_iso.split('T')[1][:5] if ist_iso else soll_zeit
                    
                    linie = dep.get('line', {}).get('name', '???').replace(" ", "")
                    
                    # Info-Text bei Verspaetung oder Ausfall
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
                
                # Sortierung nach Fahrplanzeit
                fahrplan.sort(key=lambda x: x['zeit'])
                return fahrplan
            
            elif r.status_code == 500:
                print(f"Server-Fehler 500 bei {station_name}, Versuch {versuch+1}...")
                time.sleep(5)
                continue
                
        except Exception as e:
            print(f"Verbindungsfehler bei {station_name}: {e}")
            
    return []

if __name__ == "__main__":
    print(f"Start Update: {datetime.now().strftime('%H:%M:%S')}")
    for st in stationen:
        print(f"Lade Daten fuer {st['name']}...")
        daten = hole_daten(st['id'], st['name'])
        
        filename = f"{st['name']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Datei {filename} gespeichert ({len(daten)} Eintraege).")
