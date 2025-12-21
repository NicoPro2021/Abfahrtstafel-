import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt_zeit = datetime.now().strftime("%H:%M")
    # Wir nutzen eine robustere URL-Struktur
    url = "https://v6.db.transport.rest/stops/8006654/departures?results=10&duration=120&remarks=true"
    
    try:
        # Cache-Buster, um immer frische Daten zu erzwingen
        response = requests.get(f"{url}&t={int(datetime.now().timestamp())}", timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "-", "info": jetzt_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        if not departures:
            # Plan B: Falls mit Remarks nichts kommt, versuchen wir es ohne (Basis-Daten)
            url_simple = "https://v6.db.transport.rest/stops/8006654/departures?results=6"
            departures = requests.get(url_simple, verify=False).json().get('departures', [])

        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "RT" in linie: continue # Kassel-Filter

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- Verspätungsgrund / Info ---
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            # Wir suchen nach der wichtigsten Meldung (z.B. "Notarzteinsatz", "Signalstörung")
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            if delay and delay > 0:
                minuten = f"+{int(delay/60)}"
                # Kombiniere Minuten und Grund (z.B. "+5 Signalstörung")
                info_text = f"{minuten} {grund}".strip() if grund else minuten
            else:
                info_text = grund if grund else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:40], # Genug Platz für Gründe
                "update": jetzt_zeit
            })

        return fahrplan[:6] if fahrplan else [{"zeit": "Warte", "linie": "DB", "ziel": "Suche Züge...", "gleis": "-", "info": jetzt_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
