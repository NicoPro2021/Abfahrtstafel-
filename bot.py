import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt_zeit = datetime.now().strftime("%H:%M")
    # Wir laden Abfahrten inkl. Bemerkungen (remarks)
    url = "https://v6.db.transport.rest/stops/8006654/departures?results=10&duration=120&remarks=true"
    
    try:
        response = requests.get(url, timeout=20, verify=False)
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": "Fehler", "gleis": "-", "info": jetzt_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if "RT" in linie: continue # Kassel-Filter

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- Verspätungsgrund extrahieren ---
            info_text = "pünktlich"
            delay = dep.get('delay')
            
            # Suche nach wichtigen Bemerkungen
            remarks = dep.get('remarks', [])
            wichtige_info = ""
            for r in remarks:
                # Wir filtern nach echten Störungen (Typ 'warning')
                if r.get('type') == 'warning' or r.get('summary'):
                    wichtige_info = r.get('summary') or r.get('text', '')
                    break

            if delay and delay > 0:
                minuten = f"+{int(delay/60)}"
                # Wenn wir eine Text-Info haben, hängen wir sie an oder ersetzen sie
                info_text = f"{minuten} {wichtige_info}".strip()
            elif wichtige_info:
                info_text = wichtige_info

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:30], # Auf 30 Zeichen begrenzt fürs Display
                "update": jetzt_zeit
            })

        return fahrplan[:6] if fahrplan else [{"zeit": "Warte", "linie": "DB", "ziel": "Suche Züge...", "gleis": "-", "info": jetzt_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
