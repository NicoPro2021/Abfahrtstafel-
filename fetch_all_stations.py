import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Konfiguration: Zerbst als Name, um die falsche Zinnowitz-ID (8010392) zu umgehen
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "Zerbst/Anhalt", 
    "dessau_hbf": "8010077",
    "dessau_sued": "8011382",
    "rosslau": "8010297",
    "rodleben": "8010293",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052"
}

def hole_daten(identifier, dateiname):
    # Zeitstempel für Berlin (UTC+1)
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'BahnMonitorBot/3.0'}
    
    try:
        final_id = identifier
        # Falls identifier Text ist (Zerbst), suche die ID frisch
        if not identifier.isdigit():
            s_url = f"https://v6.db.transport.rest/locations?query={identifier}&results=1"
            s_data = requests.get(s_url, headers=headers, timeout=10).json()
            if s_data:
                final_id = s_data[0]['id']
            else:
                return None

        # Abfrage der Abfahrten (3 Stunden Fenster)
        url = f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&results=50"
        r = requests.get(url, headers=headers, timeout=15).json()
        departures = r.get('departures', [])
        
        if not departures:
            return None

        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Nur Züge und Schienenersatzverkehr
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress'] and "Bus" not in line.get('name', ''):
                    continue

                planned = datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))
                actual = datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00'))
                diff = int((actual - planned).total_seconds() / 60)
                
                res.append({
                    "zeit": planned.strftime("%H:%M"), 
                    "echte_zeit": actual.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else ""), 
                    "update": u_zeit
                })
            except: continue
        return res
    except Exception as e:
        print(f"Fehler bei {dateiname}: {e}")
        return None

if __name__ == "__main__":
    for dateiname, identifier in STATIONS.items():
        print(f"Verarbeite {dateiname}...")
        daten = hole_daten(identifier, dateiname)
        # Nur speichern, wenn wir echte Daten haben (verhindert [])
        if daten is not None and len(daten) > 0:
            with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
        time.sleep(1)
