import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # --- HIER IST DIE ÄNDERUNG ---
    # Zerbst/Anhalt ID: 8010405
    station_id = "8010405" 
    
    # Erhöhte Dauer auf 180 Min, falls in Zerbst gerade wenig fährt
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&duration=180&remarks=true"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "Bus" in linie: continue

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            ist_zeit = zeit_roh.split('T')[1][:5]
            ziel = dep.get('direction', 'Ziel')[:20]
            gleis = str(dep.get('platform') or "-")
            
            delay = dep.get('delay')
            info_text = ""
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            elif delay and delay >= 60:
                info_text = f"+{int(delay/60)}"

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text.strip(),
                "update": u_zeit
            })

        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "API", "ziel": "Error", "gleis": "-", "info": str(e)[:10], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
