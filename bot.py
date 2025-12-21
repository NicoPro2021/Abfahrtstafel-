import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt = datetime.now().strftime("%H:%M")
    # Wir nutzen den stabilsten Endpunkt der DB direkt
    # duration=120 (2 Stunden), remarks=true (Gründe)
    url = "https://db.transport.rest/stops/8006654/departures?duration=120&remarks=true"
    
    try:
        # Wir fügen einen Zeitstempel hinzu, um den Cache zu zwingen
        res = requests.get(f"{url}&t={int(datetime.now().timestamp())}", timeout=15, verify=False)
        
        # Falls die API leer antwortet oder spinnt
        if res.status_code != 200:
            return [{"zeit": "Err", "linie": "DB", "ziel": "Server Busy", "gleis": "-", "info": jetzt}]

        data = res.json()
        # Falls die API uns wieder nach Kassel schickt (RT4), filtern wir das hier hart weg
        departures = [d for d in data.get('departures', []) if "RT" not in d.get('line', {}).get('name', '')]
        
        fahrplan = []
        for dep in departures:
            # Zeit & Verspätung
            p_time = dep.get('plannedWhen', '')
            zeit = p_time.split('T')[1][:5] if 'T' in p_time else "--:--"
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- Verspätungsgründe ---
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            # Wir suchen den Text für den Grund
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                info_text = f"+{int(delay/60)} {grund}".strip()
            elif grund:
                info_text = grund

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:35], # Begrenzt für das Display
                "update": jetzt
            })

        if not fahrplan:
            return [{"zeit": "Check", "linie": "DB", "ziel": "Kein Zug gef.", "gleis": "-", "info": jetzt}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": "Retry...", "gleis": "-", "info": jetzt}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
