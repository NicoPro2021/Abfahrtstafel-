import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt = datetime.now()
    update_zeit = jetzt.strftime("%H:%M")
    
    # Wir nutzen die Hafas-Schnittstelle über einen Proxy, der remarks (Gründe) unterstützt
    # Die ID 8006654 ist Zerbst. Wir hängen 'duration' an, um mehr Züge zu sehen.
    url = "https://v6.db.transport.rest/stops/8006654/departures?duration=120&remarks=true&results=10"
    
    try:
        # Der entscheidende Trick: Wir senden einen Header mit, der 'de' (Deutschland) erzwingt
        headers = {
            'Accept-Language': 'de',
            'User-Agent': 'Zerbst-Fahrplan-Monitor-v2'
        }
        
        # Cache-Buster, um das "Kassel-Problem" zu umgehen
        response = requests.get(f"{url}&t={int(jetzt.timestamp())}", headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "-", "info": update_zeit}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Sicherheits-Check: Wenn es RT4 ist, überspringen (Kassel-Fehler)
            if "RT" in linie or "Kassel" in dep.get('direction', ''):
                continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung und Gründe
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            # Den ersten wichtigen Grund suchen
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                minuten = f"+{int(delay/60)}"
                info_text = f"{minuten} {grund}".strip()
            elif grund:
                info_text = grund

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": update_zeit
            })

        # Falls der Kassel-Filter alles gelöscht hat, geben wir eine Info aus
        if not fahrplan:
            return [{"zeit": "00:00", "linie": "INFO", "ziel": "Kein Zug in 2h", "gleis": "-", "info": update_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "-", "info": update_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
