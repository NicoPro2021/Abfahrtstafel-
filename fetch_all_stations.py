import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- ALLE STATIONEN IN KLEINSCHREIBUNG ---
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
    jetzt = datetime.now(timezone.utc)
    # 10 Stunden Zeitfenster abfragen
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=600&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # Nur Züge zeigen, die noch nicht weg sind (2 Min Puffer)
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)): continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay', 0)
            
            info_text = ""
            if cancelled:
                info_text = "FÄLLT AUS"
            elif delay and delay >= 60:
                info_text = f"+{int(delay / 60)} Min"

            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text
            })

        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:12]

    except Exception as e:
        print(f"Fehler bei {station_name}: {e}")
        return None

if __name__ == "__main__":
    for st in stationen:
        print(f"Lade {st['name']}...")
        daten = hole_daten(st['id'], st['name'])
        
        # WICHTIG: Er schreibt die Datei IMMER. 
        # Wenn daten eine leere Liste [] sind, wird die Station als "nicht bedient" erkannt.
        if daten is not None:
            filename = f"{st['name']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            print(f"Gespeichert: {filename} ({len(daten)} Zuege)")
