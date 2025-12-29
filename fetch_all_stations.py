
import requests
import json
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION ---
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

def hole_daten(station_id):
    jetzt = datetime.now(timezone.utc)
    # 8 Stunden Zeitraum abfragen (480 min)
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            # Filter: Züge die mehr als 5 Minuten weg sind ignorieren
            if zug_zeit_obj < (jetzt - timedelta(minutes=5)): continue

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
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text
            })

        # Nach Zeit sortieren
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:12] # Top 12 Züge

    except Exception as e:
        print(f"Fehler bei Station {station_id}: {e}")
        return []

if __name__ == "__main__":
    for st in stationen:
        print(f"Update für {st['name']}...")
        daten = hole_daten(st['id'])
        if daten:
            with open(f"{st['name']}.json", 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
