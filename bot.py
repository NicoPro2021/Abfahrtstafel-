import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # Zerbst/Anhalt VBB-ID: 900000143501
    # Wir fragen 240 Minuten (4 Stunden) ab, um die Liste voll zu bekommen
    url = "https://v6.vbb.transport.rest/stops/900000143501/departures?duration=240&remarks=true&results=15"
    
    try:
        # Cache-Buster und User-Agent um Blockaden zu umgehen
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(f"{url}&t={int(datetime.now().timestamp())}", headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Warte", "linie": "VBB", "ziel": "Server Last", "gleis": "-", "info": u_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Harte Filterung gegen den Kassel-Bug (RT-Linien ignorieren)
            if "RT" in linie:
                continue

            # Zeit & Ziel
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung & Gründe
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
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
                "info": info_text[:35],
                "update": u_zeit
            })

        if not fahrplan:
            return [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge aktuell", "gleis": "-", "info": u_zeit}]

        return fahrplan[:10] # Wir geben jetzt die nächsten 10 Züge zurück!

    except Exception as e:
        return [{"zeit": "Error", "linie": "Bot", "ziel": "Verbindung..", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
