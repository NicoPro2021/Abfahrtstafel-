import requests, json
from datetime import datetime, timezone

def run():
    # Wir nutzen eine breitere Abfrage für Leipzig, um S-Bahn und Fernbahn zu erwischen
    url = "https://v6.db.transport.rest/stops/8010205/departures?duration=600&results=30&suburban=true&regional=true&national=true"
    
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Wir nehmen ALLES außer Busse und Trams
            product = d.get('line', {}).get('product', '')
            if product in ['bus', 'tram']: continue
            
            # Zeit-Logik
            soll_iso = d.get('plannedWhen') or d.get('when')
            if not soll_iso: continue
            zeit = soll_iso.split('T')[1][:5]
            
            # Ziel-Korrektur (Leipzig Hbf (tief) -> Leipzig Hbf)
            ziel = d.get('direction', 'Ziel unbekannt').replace(" (tief)", "")
            
            res.append({
                "zeit": zeit, 
                "linie": d.get('line', {}).get('name', '???'), 
                "ziel": ziel[:18], 
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else ""
            })
        
        # Falls die Liste leer ist, schreiben wir einen Test-Eintrag!
        if not res:
            res.append({
                "zeit": "--:--",
                "linie": "INFO",
                "ziel": "Keine Züge gefunden",
                "gleis": "!",
                "info": "API Check"
            })

        # Zeitstempel hinzufügen, damit die Datei sich IMMER ändert
        for item in res:
            item["last_run"] = datetime.now(timezone.utc).strftime("%H:%M:%S")

        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
            
        print(f"Leipzig: {len(res)} Einträge gespeichert.")

    except Exception as e:
        print(f"Kritischer Fehler Leipzig: {e}")

if __name__ == "__main__":
    run()
