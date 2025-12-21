import requests
import json
import urllib3
from datetime import datetime

# Deaktiviert die Warnmeldungen für unsichere Verbindungen
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Zerbst/Anhalt ID
    STATION_ID = "8006654"
    # Wir nutzen einen stabilen HTTPS-Endpunkt
    url = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?results=10&duration=120"
    
    jetzt_zeit = datetime.now().strftime("%H:%M")
    
    try:
        # Wir versuchen die Anfrage ohne SSL-Verifizierung (verify=False)
        # Das löst den HTTPSConnection/SSL Fehler auf GitHub
        response = requests.get(
            url, 
            timeout=25, 
            verify=False, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": jetzt_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            # Schutz gegen die Kassel-Daten
            if "RT4" in linie: continue

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
            return [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt_zeit}]

        return fahrplan[:6]

    except Exception as e:
        # Zeigt uns den genauen Fehler an, falls es immer noch kracht
        return [{"zeit": "Error", "linie": "Final", "ziel": str(e)[:20], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
