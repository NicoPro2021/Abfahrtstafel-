import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # ID 8010205 ist der Leipziger Hauptbahnhof (fest vergeben)
    echte_id = "8010205"
    
    try:
        # Wir fragen direkt mit der ID ab - ohne vorherige Suche!
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=20&remarks=true"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Filter: Keine Busse oder Straßenbahnen
            product = dep.get('line', {}).get('product', '')
            if product in ['bus', 'tram']: continue

            ist_w = dep.get('when') or dep.get('plannedWhen')
            if not ist_w: continue
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            cancelled = dep.get('cancelled', False)
            
            info_text = ""
            if cancelled:
                info_text = "FÄLLT AUS"
            elif ist_zeit != soll_zeit:
                info_text = f"ca. {ist_zeit}"

            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit, 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text, 
                "update": u_zeit
            })

        # Sortieren nach Zeit
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:15]

    except Exception as e:
        print(f"Fehler bei Leipzig: {e}")
        return []

if __name__ == "__main__":
    daten = hole_daten()
    # WICHTIG: Die Datei wird jetzt definitiv geschrieben/überschrieben
    with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
