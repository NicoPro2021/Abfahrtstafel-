import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Die korrekten IDs für Sachsen-Anhalt (EVA-Nummern)
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "8010392",
    "dessau_hbf": "8010077",
    "dessau_sued": "8011382",
    "rosslau": "8010297",
    "rodleben": "8010293",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052"
}

def hole_daten(station_id, name):
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # Direkte ID-Abfrage verhindert Verwechslungen mit Riesa/Dresden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=50&remarks=true"
        headers = {'User-Agent': 'BahnMonitor-Bot-V1'}
        r = requests.get(url, headers=headers, timeout=15).json()
        
        res = []
        departures = r.get('departures', [])
        
        for d in departures:
            try:
                line = d.get('line', {})
                # Filter: Wir wollen meist nur Züge (S-Bahn, RB, RE, IC, ICE)
                # Falls du auch Busse willst, lass diese Zeile weg:
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress']:
                    continue

                linename = line.get('name', '').replace(" ", "")
                ziel = d.get('direction', '')
                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                
                if not soll_raw: continue
                
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                info_feld = "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else "")
                
                res.append({
                    "zeit": soll_dt.strftime("%H:%M"), 
                    "echte_zeit": ist_dt.strftime("%H:%M"), 
                    "linie": linename, 
                    "ziel": ziel[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info_feld, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: 
                continue
        return res
    except Exception as e:
        print(f"Fehler bei {name} ({station_id}): {e}")
        return []

if __name__ == "__main__":
    for dateiname, s_id in STATIONS.items():
        print(f"Aktualisiere {dateiname}...")
        daten = hole_daten(s_id, dateiname)
        
        with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        
        time.sleep(1) # Schutzpause für die API

    print("Alle Daten wurden korrekt für Sachsen-Anhalt geladen.")
