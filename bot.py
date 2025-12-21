import os
import sys
import json
from datetime import datetime, timedelta, timezone

# 1. ERZWINGE INSTALLATION (Damit ModuleNotFoundError nie wieder kommt)
try:
    from pyhafas import HafasClient
    from pyhafas.profile import VBBProfile
except ImportError:
    os.system(f"{sys.executable} -m pip install pyhafas")
    from pyhafas import HafasClient
    from pyhafas.profile import VBBProfile

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # 2. NUTZE VBB (Viel stabiler als DB-Server)
    client = HafasClient(VBBProfile())
    station_id = "8010405" # Zerbst

    try:
        departures = client.departures(
            station=station_id,
            date=datetime.now(),
            duration=120
        )
        
        fahrplan = []
        for dep in departures:
            soll_zeit = dep.dateTime.strftime("%H:%M")
            
            # Verspätung berechnen
            delay_min = 0
            ist_zeit = soll_zeit
            if dep.delay:
                delay_min = int(dep.delay.total_seconds() / 60)
                ist_zeit = (dep.dateTime + dep.delay).strftime("%H:%M")

            linie = dep.name.replace(" ", "")
            ziel = dep.direction[:20] if dep.direction else "Ziel"
            gleis = dep.platform if dep.platform else "-"

            # Info-Text Logik
            info_text = ""
            if dep.cancelled:
                info_text = "FÄLLT AUS!"
            elif delay_min > 0:
                info_text = f"+{delay_min} Min"

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach echter Zeit
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:15]

    except Exception as e:
        # Notfall-Rückgabe falls Server doch blockt
        return [{"zeit": "Err", "linie": "VBB", "ziel": "Verbindung", "gleis": "-", "info": "Server blockt", "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
