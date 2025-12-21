import os
import sys

# --- DER TRICK: Installiert pyhafas automatisch, falls es fehlt ---
try:
    from pyhafas import HafasClient
except ImportError:
    os.system(f"{sys.executable} -m pip install pyhafas")
    from pyhafas import HafasClient

import json
from datetime import datetime, timedelta, timezone
from pyhafas.profile import DBProfile

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    client = HafasClient(DBProfile())
    
    # Station ID Zerbst
    station_id = "8010405" 

    try:
        departures = client.departures(
            station=station_id,
            date=datetime.now(),
            duration=120
        )
        
        fahrplan = []
        for dep in departures:
            soll_zeit = dep.dateTime.strftime("%H:%M")
            ist_zeit = soll_zeit
            delay_min = 0
            if dep.delay:
                delay_min = int(dep.delay.total_seconds() / 60)
                ist_zeit = (dep.dateTime + dep.delay).strftime("%H:%M")

            linie = dep.name.replace(" ", "")
            ziel = dep.direction[:20] if dep.direction else "Ziel unbekannt"
            gleis = dep.platform if dep.platform else "-"

            hinweise = []
            if dep.remarks:
                for rm in dep.remarks:
                    if hasattr(rm, 'text') and rm.text:
                        txt = rm.text.strip()
                        if "Fahrrad" not in txt and txt not in hinweise:
                            hinweise.append(txt)

            grund = " | ".join(hinweise)
            
            if dep.cancelled:
                info_text = "FÄLLT AUS!"
            elif delay_min > 0:
                info_text = f"+{delay_min} Min: {grund}" if grund else f"+{delay_min} Min"
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

        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:15]

    except Exception as e:
        return [{"zeit": "Err", "linie": "HAFAS", "ziel": "Error", "gleis": "-", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
        json.dump(daten, f, ensure_ascii=False, indent=4)
