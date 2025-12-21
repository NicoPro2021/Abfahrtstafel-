import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    try:
        # Schritt 1: Suche die ID für "Zerbst/Anhalt" live
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        location_data = suche_res.json()
        
        if not location_data:
            return [{"zeit": "Err", "linie": "ID", "ziel": "Nicht gef.", "gleis": "-", "info": u_zeit}]
        
        echte_id = location_data[0]['id']
        
        # Schritt 2: Abfahrten für diese ID laden (300 Min = 5 Std Fenster)
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=300&results=20"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Wir nehmen ALLES außer Fernverkehr (ICE/IC) und die Kassel-RT
            if any(x in linie for x in ["ICE", "IC", "RT"]):
                continue
                
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")
            ziel = dep.get('direction', 'Ziel unbekannt')
            
            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": "pünktlich"
            })

        if not fahrplan:
            # Wenn immer noch leer, zeigen wir die ersten 3 Treffer egal was es ist
            for dep in departures[:3]:
                fahrplan.append({
                    "zeit": "DEBUG",
                    "linie": dep.get('line', {}).get('name', '??'),
                    "ziel": dep.get('direction', '')[:15],
                    "gleis": "-",
                    "info": "Check"
                })

        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
