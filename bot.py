import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # Wir nutzen die HAFAS-Schnittstelle für Zerbst/Anhalt (ID: 8006654)
    # Wir laden 2 Stunden (120 Min)
    url = "https://v6.db.transport.rest/stops/8006654/departures?duration=120&results=15"
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(r.status_code), "gleis": "-", "info": u_zeit}]
        
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Wir nehmen die Linie (RE13, RB42 etc.)
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # WICHTIG: Wir filtern alles aus, was nach Berlin-Südkreuz aussieht
            # (Diese Züge haben oft Linien wie RB10, RE3, ICE...)
            verbotene_linien = ["ICE", "IC", "RE3", "RB10", "RE4", "RB14", "RE5", "RB24"]
            if any(v in linie for v in verbotene_linien):
                continue
            
            # Zeit und Gleis
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")
            
            # Ziel
            ziel = dep.get('direction', 'Ziel unbekannt')
            
            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": "pünktlich"
            })

        if not fahrplan:
            # Wenn immer noch leer, geben wir die Rohdaten der ersten 3 Züge aus, 
            # damit wir sehen, was die Bahn überhaupt schickt
            for dep in departures[:3]:
                w = dep.get('when') or dep.get('plannedWhen', '')
                fahrplan.append({
                    "zeit": w.split('T')[1][:5] if 'T' in w else "??",
                    "linie": dep.get('line', {}).get('name', '??'),
                    "ziel": "Debug Mode",
                    "gleis": "-",
                    "info": u_zeit
                })

        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
