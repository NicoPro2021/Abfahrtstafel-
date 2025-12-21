import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt_zeit = datetime.now().strftime("%H:%M")
    
    try:
        # SCHRITT 1: Wir suchen die aktuell gültige ID für Zerbst
        search_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        s_res = requests.get(search_url, timeout=15, verify=False)
        
        if s_res.status_code == 200 and len(s_res.json()) > 0:
            station_id = s_res.json()[0].get('id')
        else:
            station_id = "8006654" # Fallback auf Standard-ID

        # SCHRITT 2: Abfahrten laden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=10&duration=120"
        t_url = f"{url}&t={int(datetime.now().timestamp())}"
        
        response = requests.get(t_url, timeout=15, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "-", "info": jetzt_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            # Kassel-Daten (RT4) hart ignorieren
            if "RT" in linie: continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info,
                "update": jetzt_zeit
            })

        if not fahrplan:
            return [{"zeit": "Noch", "linie": "Keine", "ziel": "Züge gefunden", "gleis": "-", "info": jetzt_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
