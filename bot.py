import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Aktuelle Zeit MIT Zeitzone (UTC) für den Vergleich
    jetzt = datetime.now(timezone.utc)
    u_zeit = jetzt.strftime("%H:%M")
    
    try:
        # Schritt 1: ID für Zerbst finden
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        res_json = suche_res.json()
        if not res_json:
            return [{"zeit": "Err", "linie": "Bot", "ziel": "Station nicht gef.", "gleis": "-", "info": "Error"}]
        echte_id = res_json[0]['id']
        
        # Schritt 2: Abfahrten laden 
        # duration=300 (5 Stunden), results=30 (genügend Puffer für viele Züge)
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=300&results=30"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Zeit-Objekt für den "Rückstau-Filter"
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # Züge, die schon mehr als 2 Minuten weg sind, ignorieren
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)):
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            # Fernverkehr (ICE/IC) in Zerbst meist nicht relevant, sonst Zeile entfernen
            if any(x in linie for x in ["ICE", "IC", "RT"]): continue
            
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            cancelled = dep.get('cancelled', False)
            if cancelled:
                info_text = "fällt aus"
            else:
                delay = dep.get('delay')
                # Info-Text nur bei Verspätung (z.B. +5)
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

        # Nach der tatsächlichen Zeit sortieren
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # HIER DIE ÄNDERUNG: Gib die nächsten 10 Züge zurück
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
