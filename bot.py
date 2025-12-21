import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Aktuelle Zeit MIT Zeitzone (UTC)
    jetzt = datetime.now(timezone.utc)
    u_zeit = jetzt.strftime("%H:%M")
    
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
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Fehlerkorrektur: ISO-Zeit in UTC umwandeln für den Vergleich
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # Vergleich: Nur Züge nehmen, die noch nicht oder gerade eben abgefahren sind
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)):
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if any(x in linie for x in ["ICE", "IC", "RT"]): continue
            
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            cancelled = dep.get('cancelled', False)
            if cancelled:
                info_text = "fällt aus"
            else:
                delay = dep.get('delay')
                info_text = f"+{int(delay / 60)}" if delay and delay > 0 else ""

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:8]

    except Exception as e:
        # Fehlerausgabe für das JSON
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
