import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = jetzt.strftime("%H:%M")
    
    try:
        # 1. Zerbst ID holen
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # 2. MEHR DATEN ABFRAGEN: 
        # duration=480 (8 Stunden vorraus)
        # results=40 (genügend Puffer für alle Regionalbahnen)
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=40&remarks=true"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Zeit-Objekt für den Filter
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # Nur Züge nehmen, die noch nicht weg sind
            if zug_zeit_obj < (jetzt - timedelta(minutes=1)):
                continue

            # Linie filtern (Regionalverkehr Zerbst)
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # Info-Logik (Verspätung oder Ausfall)
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

        # Sortieren nach echter Ankunftszeit
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # JETZT: Die nächsten 10 Züge zurückgeben (statt nur 2!)
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
