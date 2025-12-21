import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Wir nutzen die v5 Schnittstelle, die bei vielen älteren Bahnhöfen zuverlässiger ist
    # Zerbst/Anhalt ID: 8006654
    url = "https://v5.db.transport.rest/stops/8006654/departures?results=10&duration=120"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    try:
        # Cache-Buster mit aktuellem Zeitstempel
        t_url = f"{url}&t={int(datetime.now().timestamp())}"
        response = requests.get(t_url, headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # V5 liefert die Daten oft direkt als Liste oder in einem Objekt
        departures = data if isinstance(data, list) else data.get('departures', [])
        
        fahrplan = []
        update_zeit = datetime.now().strftime("%H:%M")

        for dep in departures:
            # Wir holen die Linie (z.B. RE 13)
            linie_obj = dep.get('line', {})
            linie = linie_obj.get('name', '???')
            
            # Ziel & Zeit
            ziel = dep.get('direction', 'Unbekannt')
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            
            # Filter gegen die Kassel-Testdaten
            if "RT4" in linie or "Wolfhagen" in ziel:
                continue

            gleis = str(dep.get('platform') or "-")
            
            # Verspätung prüfen
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

        # Wenn die Liste immer noch leer ist, bauen wir eine "Nacht-Info"
        if not fahrplan:
            return [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge aktuell", "gleis": "-", "info": update_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
