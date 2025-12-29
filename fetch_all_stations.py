import requests
import json
import time
from datetime import datetime, timedelta, timezone

# --- STATIONSLISTE MIT DEFINITIV KORREKTEN IDs (STAND 29.12.2025) ---
stationen = [
    {"name": "zerbst", "id": "8010390"},           # Zerbst/Anhalt (Magdeburg-Leipzig)
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
    jetzt = datetime.now(timezone.utc)
    # 12 Stunden Zeitraum (720 Min), damit wir immer Züge finden
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=720&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Nur Züge (RE, RB, S), keine Busse
            if dep.get('line', {}).get('product') == 'bus':
                continue

            ist_w = dep.get('when') or dep.get('plannedWhen')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            # Züge die bereits weg sind ignorieren
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
                info_text = f"ca. {ist_zeit}"

            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text
            })

        # Nach Zeit sortieren
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:12]

    except Exception as e:
        print(f"Fehler bei {station_name}: {e}")
        return []

if __name__ == "__main__":
    for st in stationen:
        print(f"Lade {st['name']}...")
        daten = hole_daten(st['id'], st['name'])
        
        # WICHTIG: Die Datei wird IMMER kleingeschrieben gespeichert!
        filename = f"{st['name']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Gespeichert: {filename} ({len(daten)} Züge)")
