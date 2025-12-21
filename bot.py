import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Wir probieren die ID mit führenden Nullen, das hilft oft bei HAFAS-Servern
    STATION_ID = "8006654"
    # Wir erhöhen die duration auf 240 Min (4 Std), um sicherzugehen, dass Züge gefunden werden
    url = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?results=10&duration=240"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    try:
        # Cache-Buster hinzufügen
        t_url = f"{url}&t={int(datetime.now().timestamp())}"
        response = requests.get(t_url, headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        departures = data.get('departures', [])
        
        # Falls leer, versuchen wir es über die Namenssuche (Fallback)
        if not departures:
            search_url = f"https://v6.db.transport.rest/locations?query=Zerbst&results=1"
            s_res = requests.get(search_url, verify=False).json()
            if s_res:
                new_id = s_res[0].get('id')
                url = f"https://v6.db.transport.rest/stops/{new_id}/departures?results=10&duration=240"
                departures = requests.get(url, verify=False).json().get('departures', [])

        fahrplan = []
        update_zeit = datetime.now().strftime("%H:%M")

        for dep in departures:
            # Filtere Kassel-Daten aus, falls sie wieder auftauchen
            linie = dep.get('line', {}).get('name', '???')
            ziel = dep.get('direction', 'Unbekannt')
            
            if "RT4" in linie or "Wolfhagen" in ziel:
                continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            gleis = str(dep.get('platform') or "-")
            
            delay = dep.get('delay')
            info = "pünktlich"
            if delay and delay > 0:
                info = f"+{int(delay/60)}"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie.replace(" ", ""),
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": info,
                "update": update_zeit
            })

        return fahrplan[:6] if fahrplan else [{"zeit": "Keine", "linie": "DB", "ziel": "Züge aktuell", "gleis": "-", "info": update_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
