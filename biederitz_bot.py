import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    # Update-Zeit für die Anzeige (MEZ/MESZ)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    try:
        # Schritt 1: ID für Biederitz suchen
        suche_url = "https://v6.db.transport.rest/locations?query=Biederitz&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return []
            
        station_id = suche_data[0]['id']
        
        # Schritt 2: Abfahrten für die nächsten 60 Minuten laden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=60&results=100&remarks=true"
        r = requests.get(url, timeout=15).json()
        
        res = []
        for d in r.get('departures', []):
            try:
                line = d.get('line', {})
                name = line.get('name', '').replace(" ", "")
                ziel = d.get('direction', '')
                
                # Zeit-Berechnung
                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # Info-Feld: +Minuten oder FÄLLT AUS
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
            except: continue
        return res
    except: 
        return []

if __name__ == "__main__":
    daten = hole_daten()
    # Speichert die Daten in biederitz.json
    with open('biederitz.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
