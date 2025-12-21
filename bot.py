import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # Zerbst/Anhalt ID
    station_id = "8010405" 
    
    # Wir nutzen einen anderen API-Endpunkt (Hafas-Rest)
    # Dieser ist oft weniger streng als der Haupt-DB-Server
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&duration=120&remarks=true"

    try:
        # Wir setzen einen "User-Agent", damit wir wie ein Browser aussehen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            # Zeit holen
            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            ist_zeit = zeit_roh.split('T')[1][:5]
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            ziel = dep.get('direction', 'Ziel')[:20]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung und Infos
            delay = dep.get('delay')
            info_text = ""
            
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            elif delay and delay >= 60:
                info_text = f"+{int(delay/60)} Min"
            
            # Bemerkungen (nur wichtige)
            remarks = dep.get('remarks', [])
            for rm in remarks:
                if rm.get('type') == 'warning':
                    info_text += f" ! {rm.get('summary', '')}"

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text.strip(),
                "update": u_zeit
            })

        return fahrplan if fahrplan else [{"zeit": "Wait", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": "", "update": u_zeit}]

    except Exception as e:
        return [{"zeit": "Err", "linie": "API", "ziel": "Fehler", "gleis": "-", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
