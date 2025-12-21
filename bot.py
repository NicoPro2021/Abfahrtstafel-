import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir nutzen die VBB Schnittstelle für Zerbst/Anhalt (ID: 900000143501 oder 8006654)
# Hier erzwingen wir die Abfrage über ein anderes System
URL = "https://v6.vbb.transport.rest/stops/8006654/departures?results=6&duration=120"

def hole_daten():
    try:
        headers = {'User-Agent': 'ZerbstFahrplanBot/1.0'}
        # Wir hängen wieder einen Cache-Buster an
        t_url = f"{URL}&t={int(datetime.now().timestamp())}"
        response = requests.get(t_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        jetzt = datetime.now().strftime("%H:%M:%S")

        for dep in departures:
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw else "--:--"
            
            # Linie (z.B. RE13)
            line_obj = dep.get('line', {})
            linie = line_obj.get('name', '???')
            
            # Ziel
            ziel = dep.get('direction', 'Unbekannt')
            
            # Gleis
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

        # Finaler Check: Wenn immer noch RT4 kommt, stimmt was mit der ID nicht
        if fahrplan and "RT" in fahrplan[0]['linie']:
             return [{"zeit": "ID", "linie": "CHECK", "ziel": "Immer noch Kassel", "gleis": "!", "info": jetzt}]

        return fahrplan if fahrplan else [{"zeit": "00:00", "linie": "VBB", "ziel": "Keine Züge", "gleis": "-", "info": jetzt}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("VBB-Abfrage für Zerbst beendet.")
