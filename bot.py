import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir suchen jetzt direkt nach dem Namen Zerbst/Anhalt, um die Kassel-Daten zu verdrängen
URL = "https://v6.db.transport.rest/stops/8006654/departures?results=6&duration=120"

def hole_daten():
    try:
        # Der Header simuliert einen echten Browser, um keine Standard-Testdaten zu bekommen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
        
        # Wir hängen einen Zeitstempel an die URL (?t=...), damit der Server uns keine alte Version schickt
        timestamp_url = f"{URL}&t={int(datetime.now().timestamp())}"
        response = requests.get(timestamp_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        jetzt = datetime.now().strftime("%H:%M:%S")

        for dep in departures:
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw else "--:--"
            
            # Linie und Ziel
            linie = dep.get('line', {}).get('name', '???')
            ziel = dep.get('direction', 'Unbekannt')
            gleis = dep.get('platform') or "-"
            
            # Verspätung
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": str(gleis),
                "info": info,
                "update": jetzt
            })

        # Falls der Server uns WIEDER Kassel schickt (RT4), geben wir eine Warnung aus
        if fahrplan and fahrplan[0]['linie'] == "RT4":
             return [{"zeit": "12:34", "linie": "FEHLER", "ziel": "Falsche Stadt (Kassel)", "gleis": "!", "info": jetzt}]

        return fahrplan if fahrplan else [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Versuch Zerbst-Anhalt erfolgreich beendet.")
