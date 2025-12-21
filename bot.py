import requests
import json
import time
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    station_id = "8010405" 
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&duration=180&remarks=true"

    # 3 Versuche, falls die Verbindung hakt
    for versuch in range(3):
        try:
            headers = {'User-Agent': 'Bahn-Monitor-Zerbst'}
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            departures = data.get('departures', [])
            if not departures:
                return [{"zeit": u_zeit, "linie": "INFO", "ziel": "Keine Züge", "gleis": "-", "info": ""}]

            fahrplan = []
            for dep in departures:
                linie = dep.get('line', {}).get('name', '???').replace(" ", "")
                if "Bus" in linie: continue

                zeit_roh = dep.get('when') or dep.get('plannedWhen')
                if not zeit_roh: continue
                
                soll_zeit = zeit_roh.split('T')[1][:5]
                ziel = dep.get('direction', 'Ziel')[:15]
                gleis = str(dep.get('platform') or "-")
                
                delay = dep.get('delay')
                info_text = f"+{int(delay/60)}" if delay and delay >= 60 else ""

                fahrplan.append({
                    "zeit": soll_zeit,
                    "linie": linie,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info_text,
                    "update": u_zeit
                })

            fahrplan.sort(key=lambda x: x['zeit'])
            return fahrplan[:10]

        except Exception as e:
            print(f"Versuch {versuch + 1} fehlgeschlagen: {e}")
            time.sleep(5) # 5 Sekunden warten vor Neustart
            continue
    
    # Wenn alle 3 Versuche scheitern, gib keinen Fehler aus, sondern behalte das alte Format
    return [{"zeit": "Err", "linie": "Bot", "ziel": "Netz-Fehler", "gleis": "-", "info": "Retry..."}]

if __name__ == "__main__":
    daten = hole_daten()
    # Nur speichern, wenn es kein Fehler-Objekt ist (optional)
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
