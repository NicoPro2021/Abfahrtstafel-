import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir nutzen eine spezialisierte API für deutsche Bahnhöfe
# Diese ID ist fest für Zerbst/Anhalt hinterlegt
URL = "https://db-live.f-bit.de/api/v1/station/8006654/departures"

def hole_daten():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        # Anfrage mit Timeout
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            # Plan B: Wenn die Spezial-API nicht will, nehmen wir einen stabilen Proxy
            URL_PROXY = "https://v6.db.transport.rest/stops/8006654/departures?results=6"
            response = requests.get(URL_PROXY, headers=headers, timeout=15)
            if response.status_code != 200:
                return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # Manche APIs liefern direkt eine Liste, manche ein Objekt mit 'departures'
        items = data.get('departures', data) if isinstance(data, dict) else data
        
        fahrplan = []
        jetzt = datetime.now().strftime("%H:%M:%S")

        for dep in items[:6]:
            # Wir bauen die Daten so zusammen, dass sie exakt deinem Format entsprechen
            zeit = dep.get('time') or dep.get('when', '--:--')
            if 'T' in zeit: zeit = zeit.split('T')[1][:5]
            
            linie = dep.get('train') or dep.get('line', {}).get('name', '???')
            ziel = dep.get('destination') or dep.get('direction', 'Unbekannt')
            gleis = str(dep.get('platform', '-'))
            
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie.replace(" ", ""),
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": info,
                "update": jetzt
            })

        return fahrplan if fahrplan else [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Update für Zerbst/Anhalt abgeschlossen.")
