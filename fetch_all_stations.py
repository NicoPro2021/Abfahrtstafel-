import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Wir nutzen jetzt IDs statt Namen, um die [] Fehler zu vermeiden
# Diese Nummern sind die eindeutigen Bahnhofs-Kennungen (EVA)
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "zerbst": "8013389",
    "dessau_hbf": "8010077",
    "dessau_sued": "8011361",
    "rosslau": "8010302",
    "rodleben": "8012777",          # ID für Rodleben Bahnhof
    "magdeburg_neustadt": "8010226", # ID für MD-Neustadt
    "magdeburg_herrenkrug": "8013455", # ID für MD-Herrenkrug
    "biederitz": "8010047",
    "pretzier_altm": "8012673"
}

def hole_daten(station_id, dateiname):
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # Wir fragen direkt mit der ID ab - das ist 100% treffsicher
        # duration=120 zeigt Züge der nächsten 2 Stunden (wichtig für Rodleben!)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=50&remarks=true"
        r = requests.get(url, timeout=15).json()
        
        res = []
        departures = r.get('departures', [])
        
        if not departures:
            print(f"Hinweis: Keine Züge aktuell in {dateiname}")
            return []

        for d in departures:
            try:
                line = d.get('line', {})
                name = line.get('name', '').replace(" ", "")
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
                    "linie": name, 
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
        print(f"Fehler bei {dateiname}: {e}")
        return []

if __name__ == "__main__":
    for dateiname, s_id in STATIONS.items():
        print(f"Hole Daten für: {dateiname} (ID: {s_id})")
        daten = hole_daten(s_id, dateiname)
        
        with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        
        time.sleep(0.5) # Kurze Pause für die API

    print("Alle Stationen wurden erfolgreich geprüft.")
