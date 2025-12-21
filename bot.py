import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # Zerbst/Anhalt: 8010405 | Wannsee: 8010358
    station_id = "8010405" 
    
    # Wir fragen 20 Ergebnisse ab, um nach dem Filtern genug Züge übrig zu haben
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=25&duration=120&remarks=true"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # --- LÖSUNG 1: BUSSE RAUS ---
            # Wenn "Bus" im Namen vorkommt, überspringen wir diesen Eintrag
            if "Bus" in linie:
                continue

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            ist_zeit = zeit_roh.split('T')[1][:5]
            ziel = dep.get('direction', 'Ziel')[:20]
            gleis = str(dep.get('platform') or "-")
            
            # --- LÖSUNG 2: GRÜNDE FINDEN ---
            delay = dep.get('delay')
            info_text = ""
            
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            else:
                # Wir suchen in den 'remarks' nach dem Grund (z.B. Bauarbeiten)
                rems = dep.get('remarks', [])
                grund = ""
                for rm in rems:
                    if rm.get('type') == 'warning':
                        # Wir nehmen die Zusammenfassung des Grundes
                        grund = rm.get('summary', "")
                        break
                
                if delay and delay >= 60:
                    minuten = int(delay/60)
                    info_text = f"+{minuten} Min {grund}".strip()
                else:
                    info_text = grund

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        # Nur die nächsten 10 Züge anzeigen, damit das Display nicht überquillt
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "API", "ziel": "Fehler", "gleis": "-", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
