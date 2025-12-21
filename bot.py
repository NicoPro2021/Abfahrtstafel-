import requests
import json
import urllib3
from datetime import datetime

# Unterdrückt SSL-Warnungen, da wir verify=False nutzen
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Zerbst/Anhalt ID: 8006654
    # Wir hängen einen Zeitstempel an (&t=...), um den "Kassel-Cache" zu umgehen
    t = int(datetime.now().timestamp())
    url = f"https://v6.db.transport.rest/stops/8006654/departures?results=6&duration=120&t={t}"
    
    headers = {
        'User-Agent': 'FahrplanBot-Zerbst-ESP32',
        'Accept': 'application/json'
    }

    try:
        # verify=False hilft gegen den HTTPSConnection/SSL Fehler
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # Manche Server antworten mit einem Dictionary, manche direkt mit einer Liste
        departures = data.get('departures', []) if isinstance(data, dict) else data
        
        fahrplan = []
        update_zeit = datetime.now().strftime("%H:%M")

        for dep in departures:
            # Zeit aus "2024-05-20T18:30:00+02:00" extrahieren
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???')
            
            # Ziel & Gleis
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung berechnen
            delay = dep.get('delay')
            info = "pünktlich"
            if delay and delay > 0:
                info = f"+{int(delay/60)}"

            # Falls wir doch wieder RT4 (Kassel) sehen, ignorieren wir den Eintrag
            if "RT4" in linie or "Wolfhagen" in ziel:
                continue

            fahrplan.append({
                "zeit": zeit,
                "linie": linie.replace(" ", ""),
                "ziel": ziel,
                "gleis": gleis,
                "info": info,
                "update": update_zeit
            })

        if not fahrplan:
            return [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": update_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
    print("Update für Zerbst erfolgreich.")
