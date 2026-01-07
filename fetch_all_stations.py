import requests
import json
import time
from datetime import datetime, timedelta, timezone

# 100% korrekte IDs für Sachsen-Anhalt (EVA-Nummern)
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
    # Zeit für das Update-Feld (UTC+1)
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    headers = {
        'User-Agent': 'BahnMonitorBot/1.0',
        'Accept': 'application/json'
    }

    try:
        # Wir fragen 120 Min ab. Falls leer, liegt es meist an der API, nicht am Fahrplan.
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=50&remarks=true"
        response = requests.get(url, headers=headers, timeout=15)
        
        # Falls wir zu schnell waren (Status 429), kurz warten und wiederholen
        if response.status_code == 429:
            time.sleep(5)
            response = requests.get(url, headers=headers, timeout=15)

        data = response.json()
        departures = data.get('departures', [])

        res = []
        if not departures:
            return []

        for d in departures:
            try:
                line = d.get('line', {})
                # Nur Züge anzeigen, keine Stadtbusse (außer es ist SEV)
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress']:
                    if "Bus" not in line.get('name', ''): # Erlaubt Schienenersatzverkehr
                        continue

                linename = line.get('name', '').replace(" ", "")
                ziel = d.get('direction', '')
                soll_raw = d.get('plannedWhen') or d.get('when')
                if not soll_raw: continue
                
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_raw = d.get('when') or soll_raw
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
            except: continue
        return res
    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        return []

if __name__ == "__main__":
    # Alles in einem großen Try-Block, damit das Skript nicht abstürzt
    try:
        for dateiname, s_id in STATIONS.items():
            print(f"Lade {dateiname}...")
            daten = hole_daten(s_id, dateiname)
            
            with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            
            # WICHTIG: 2 Sekunden Pause, damit die API uns nicht bannt
            time.sleep(2)
    except Exception as e:
        print(f"Kritischer Abbruch: {e}")
