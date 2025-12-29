import requests, json
from datetime import datetime, timezone

def run():
    # Wir nutzen hier die stabilste API-Route für Großbahnhöfe
    # ID 8010205 = Leipzig Hbf
    url = "https://v6.db.transport.rest/stops/8010205/departures?duration=600&results=50&suburban=true&regional=true&national=true"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Die API liefert manchmal 'departures' oder direkt eine Liste
        departures = data.get('departures', [])
        
        res = []
        # Wir nehmen die ersten 15 gültigen Züge
        for d in departures:
            if len(res) >= 15: break
            
            # Filter: Busse und Trams raus
            product = d.get('line', {}).get('product', '')
            if product in ['bus', 'tram']: continue
            
            # Zeit extrahieren
            soll_iso = d.get('plannedWhen') or d.get('when')
            if not soll_iso: continue
            zeit = soll_iso.split('T')[1][:5]
            
            # Linie und Ziel
            linie = d.get('line', {}).get('name', '???')
            ziel = d.get('direction', 'Ziel unbekannt').replace(" (tief)", "")
            
            # Verspätung prüfen
            ist_iso = d.get('when')
            ist_zeit = ist_iso.split('T')[1][:5] if ist_iso else zeit
            info = f"ca. {ist_zeit}" if ist_zeit != zeit else ""
            if d.get('cancelled'): info = "FÄLLT AUS"

            res.append({
                "zeit": zeit, 
                "linie": linie, 
                "ziel": ziel[:20], 
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": info,
                "debug_ts": datetime.now(timezone.utc).strftime("%H:%M:%S") # Zwingt GitHub zum Update
            })
        
        # FALLBACK: Falls die API wirklich leer ist, schreiben wir Test-Daten
        # So sehen wir, ob der Bot überhaupt durchkommt
        if not res:
            res = [{
                "zeit": datetime.now(timezone.utc).strftime("%H:%M"),
                "linie": "INFO",
                "ziel": "Warten auf API...",
                "gleis": "!",
                "info": "Keine Daten empfangen",
                "debug_ts": datetime.now(timezone.utc).strftime("%H:%M:%S")
            }]

        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
            
        print(f"Leipzig Bot fertig: {len(res)} Einträge.")

    except Exception as e:
        # Selbst im Fehlerfall schreiben wir etwas, damit wir es in der JSON sehen
        error_data = [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:30]}]
        with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=4)
        print(f"Fehler bei Leipzig: {e}")

if __name__ == "__main__":
    run()
