import requests, json
from datetime import datetime, timezone

def run():
    # Wir reduzieren duration auf 120 und results auf 10, um den Server zu entlasten
    url = "https://v6.db.transport.rest/stops/8010205/departures?duration=120&results=10&suburban=true&regional=true"
    
    try:
        # Ein zweiter Versuch (Retry), falls der erste 500 liefert
        for versuch in range(2):
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                break
            import time
            time.sleep(2)
        
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Wir filtern Bus/Tram
            if d.get('line', {}).get('product') in ['bus', 'tram']: continue
            
            soll_iso = d.get('plannedWhen') or d.get('when')
            if not soll_iso: continue
            zeit = soll_iso.split('T')[1][:5]
            
            res.append({
                "zeit": zeit, 
                "linie": d.get('line', {}).get('name', '???'), 
                "ziel": d.get('direction', 'Ziel unbekannt').replace(" (tief)", "")[:20], 
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else "",
                "debug": "ok"
            })
        
        # Falls immer noch leer, schreib wenigstens eine Info-Zeile
        if not res:
            res = [{"zeit": "--:--", "linie": "DB", "ziel": "Keine Züge aktuell", "gleis": "-", "info": ""}]

        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print("Leipzig erfolgreich gespeichert.")

    except Exception as e:
        # Falls der 500er Fehler bleibt, schreiben wir eine saubere leere Liste, 
        # damit die Webseite nicht "Fehler" anzeigt, sondern einfach leer bleibt.
        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"Leipzig immer noch 500er Fehler: {e}")

if __name__ == "__main__":
    run()
