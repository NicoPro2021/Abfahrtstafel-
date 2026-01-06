import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Deine Liste der Bahnhöfe
# Ich habe hier die Suchbegriffe so präzise wie möglich gemacht
STATIONS = {
    "magdeburg_hbf": "Magdeburg Hbf",
    "leipzig_hbf": "Leipzig Hbf",
    "zerbst": "Zerbst/Anhalt",
    "dessau_hbf": "Dessau Hbf",
    "dessau_sued": "Dessau Süd",
    "rosslau": "Roßlau(Elbe)",
    "rodleben": "Rodleben",
    "magdeburg_neustadt": "Magdeburg-Neustadt",
    "magdeburg_herrenkrug": "Magdeburg-Herrenkrug",
    "biederitz": "Biederitz"
}

def hole_daten(suchbegriff):
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # SCHRITT 1: Suche nach der Station (Deine Logik)
        suche_url = f"https://v6.db.transport.rest/locations?query={suchbegriff}&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            print(f"Station nicht gefunden: {suchbegriff}")
            return []
            
        station_id = suche_data[0]['id']
        
        # SCHRITT 2: Abfahrten holen
        # duration=120 statt 60, damit bei Lücken im Fahrplan nicht sofort [] kommt
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=100&remarks=true"
        r = requests.get(url, timeout=15).json()
        
        res = []
        # Wir greifen auf r['departures'] zu, wie in deinem Code
        for d in r.get('departures', []):
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
                
                # Deine Info-Logik
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
        print(f"Fehler bei {suchbegriff}: {e}")
        return []

if __name__ == "__main__":
    for dateiname, anzeigename in STATIONS.items():
        print(f"Verarbeite: {anzeigename}...")
        daten = hole_daten(anzeigename)
        
        # Speichern unter dem jeweiligen Namen (z.B. zerbst.json)
        with open(f'{dateiname}.json', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        
        # Ganz wichtig: 1 Sekunde Pause zwischen den Bahnhöfen, 
        # damit die API uns nicht blockiert!
        time.sleep(1)

    print("Alle Stationen wurden aktualisiert.")
