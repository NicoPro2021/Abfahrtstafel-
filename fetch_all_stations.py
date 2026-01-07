import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Die IDs für Sachsen-Anhalt. Zerbst wird als Name hinterlegt, um Zinnowitz zu vermeiden.
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "Zerbst/Anhalt",  # Sonderfall: Name statt ID
    "dessau_hbf": "8010077",
    "dessau_sued": "DessauSüd",
    "rosslau": "8010297",
    "rodleben": "8010293",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052"
}

def hole_daten(id_oder_name, dateiname):
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'BahnMonitorBot/1.1'}
    
    try:
        # Schritt 1: Die richtige ID finden
        final_id = id_oder_name
        if not id_oder_name.isdigit():
            # Suche speziell für Zerbst/Anhalt
            search_url = f"https://v6.db.transport.rest/locations?query={id_oder_name}&results=1"
            search_data = requests.get(search_url, headers=headers, timeout=10).json()
            if search_data:
                final_id = search_data[0]['id']
            else:
                return []

        # Schritt 2: Abfahrten holen (mit 3h Zeitfenster gegen leere Klammern)
        url = f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&results=50&remarks=true"
        r = requests.get(url, headers=headers, timeout=15).json()
        
        departures = r.get('departures', [])
        if not departures:
            return []

        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Filter: Nur Züge und SEV-Busse
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress'] and "Bus" not in line.get('name', ''):
                    continue

                res.append({
                    "zeit": datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00')).strftime("%H:%M"), 
                    "echte_zeit": datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')).strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{int((datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')) - datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))).total_seconds() / 60)}" if int((datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00')) - datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))).total_seconds() / 60) > 0 else ""), 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
        return res
    except Exception as e:
        print(f"Fehler bei {dateiname}: {e}")
        return []

if __name__ == "__main__":
    for dateiname, identifier in STATIONS.items():
        print(f"Verarbeite {dateiname}...")
        daten = hole_daten(identifier, dateiname)
        with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        time.sleep(2) # API-Schutz
