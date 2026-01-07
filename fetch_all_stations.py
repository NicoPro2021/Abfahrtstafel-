import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Deine korrekten IDs für Sachsen-Anhalt
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
    # Zeitstempel für das Update-Feld (Berlin Zeit)
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # Header setzen, um Ban-Risiko zu minimieren
    headers = {
        'User-Agent': 'BahnMonitorBot/1.0 (Kontakt: DeinGithubName)',
        'Accept': 'application/json'
    }

    try:
        # Versuch 1: Normales Zeitfenster (120 Min)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=30&remarks=true"
        response = requests.get(url, headers=headers, timeout=15)
        
        # Falls API überlastet (Status 429), kurz warten
        if response.status_code == 429:
            time.sleep(2)
            response = requests.get(url, headers=headers, timeout=15)

        data = response.json()
        departures = data.get('departures', [])

        # Versuch 2: Falls leer, Zeitfenster massiv vergrößern (360 Min)
        if not departures:
            print(f"(!) Keine Daten für {name} bei 120min. Erweitere Suche...")
            url_long = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=360&results=20"
            departures = requests.get(url_long, headers=headers, timeout=15).json().get('departures', [])

        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Filtere nur relevante Züge (S-Bahn, Regional, Fernverkehr)
                if line.get('product') not in ['suburban', 'regional', 'national', 'nationalExpress']:
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
    for dateiname, s_id in STATIONS.items():
        print(f"Abfrage: {dateiname}...")
        daten = hole_daten(s_id, dateiname)
        
        with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        
        # WICHTIG: 1.5 Sekunden Pause zwischen den Stationen, um Ban zu vermeiden
        time.sleep(1.5)

    print("Update-Runde beendet.")
