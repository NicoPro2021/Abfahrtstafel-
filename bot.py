import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Wir nutzen die ID 8006654 und erzwingen die Abfrage
    # Wir erhöhen die Ergebnisse auf 15, um sicherzugehen, dass nach dem Filtern noch etwas übrig bleibt
    url = "https://v6.db.transport.rest/stops/8006654/departures?results=15&duration=120"
    
    # Wir nutzen eine aktuelle Zeit für den Zeitstempel
    jetzt_obj = datetime.now()
    jetzt_zeit = jetzt_obj.strftime("%H:%M")
    
    try:
        # Der entscheidende Trick: Wir hängen einen Zufallswert an, um den Cache zu leeren
        t_url = f"{url}&cache_buster={int(jetzt_obj.timestamp())}"
        
        response = requests.get(
            t_url, 
            timeout=20, 
            verify=False, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "-", "info": jetzt_zeit}]

        data = response.json()
        # Manche Server liefern die Liste direkt im Feld 'departures'
        departures = data.get('departures', [])
        
        fahrplan = []

        for dep in departures:
            # Wir suchen die Linie (z.B. RE 13)
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # WICHTIG: Wir filtern Kassel (RT4) aus, falls es noch im Cache hängt
            if "RT4" in linie:
                continue

            # Zeit extrahieren
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            
            # Ziel & Gleis
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung
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

        # Wenn wir Züge gefunden haben, geben wir sie zurück
        if fahrplan:
            return fahrplan[:6]
        
        # Falls wirklich nichts da ist, probieren wir es über eine alternative ID
        return [{"zeit": "Warte", "linie": "DB", "ziel": "Lade Zerbst...", "gleis": "-", "info": jetzt_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": jetzt_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
