import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt_zeit = datetime.now().strftime("%H:%M")
    try:
        # Wir suchen Zerbst und laden Abfahrten inkl. Bemerkungen (remarks)
        url = "https://v6.db.transport.rest/stops/8006654/departures?results=6&duration=120&remarks=true"
        response = requests.get(url, timeout=15, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": "Fehler", "gleis": "-", "info": jetzt_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "RT" in linie: continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- NEU: Verspätungsgrund suchen ---
            grund = ""
            remarks = dep.get('remarks', [])
            for r in remarks:
                if r.get('type') == 'hint' or r.get('type') == 'warning':
                    grund = r.get('text', '')
                    break # Wir nehmen den ersten wichtigen Grund

            delay = dep.get('delay')
            if delay and delay > 0:
                # Wenn ein Grund da ist, nimm den, sonst die Minuten
                info = grund if grund else f"+{int(delay/60)} Min"
            else:
                info = "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info,
                "update": jetzt_zeit
            })

        return fahrplan if fahrplan else [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
