import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    try:
        # Schritt 1: ID für Zerbst finden
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # Schritt 2: Abfahrten laden
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=300&results=20"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if any(x in linie for x in ["ICE", "IC", "RT"]): continue
            
            # Geplante Zeit (Soll)
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            
            # Tatsächliche Zeit (Ist)
            ist_w = dep.get('when')
            ist_zeit = ist_w.split('T')[1][:5] if ist_w else soll_zeit
            
            # Verspätung berechnen
            delay = dep.get('delay') # Delay in Sekunden
            if delay is not None and delay > 0:
                minuten = int(delay / 60)
                info_text = f"+{minuten}"
            else:
                info_text = "pünktlich"

            ziel = dep.get('direction', 'Ziel unbekannt')
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")
            
            fahrplan.append({
                "zeit": soll_zeit,      # Die Zeit, die im Fahrplan steht
                "echte_zeit": ist_zeit, # Die Zeit, wann er wirklich kommt
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": gleis,
                "info": info_text,      # Hier steht jetzt z.B. "+5"
                "update": u_zeit
            })

        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
