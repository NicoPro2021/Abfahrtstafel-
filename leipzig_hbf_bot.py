import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 1. Schritt: ID für Leipzig Hbf suchen
        suche_url = "https://v6.db.transport.rest/locations?query=Leipzig Hbf&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return [{"zeit": "---", "linie": "INFO", "ziel": "Station nicht gef.", "info": "", "update": u_zeit}]
        
        station_id = suche_data[0]['id']
        
        # 2. Schritt: Abfahrten für die nächsten 60 Minuten laden
        # duration=60 (1 Stunde), results=100 (damit bei dem hohen Takt nichts fehlt)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=60&results=100&remarks=true"
        r = requests.get(url, timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        for d in departures:
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
                
                # Deine Logik: +Minuten bei Verspätung, sonst leer
                info_feld = ""
                if d.get('cancelled'):
                    info_feld = "FÄLLT AUS"
                elif diff > 0:
                    info_feld = f"+{diff}"

                # Gleis-Bereinigung für Leipzig (tief/oben)
                gleis_raw = str(d.get('platform') or d.get('plannedPlatform') or "-")
                gleis = gleis_raw.replace(" (tief)", " t")

                res.append({
                    "zeit": soll_dt.strftime("%H:%M"), 
                    "echte_zeit": ist_dt.strftime("%H:%M"), 
                    "linie": name, 
                    "ziel": ziel[:18], 
                    "gleis": gleis, 
                    "info": info_feld, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue

        if not res:
            res = [{"zeit": "---", "linie": "INFO", "ziel": "Keine Abfahrten in 60min", "info": "", "update": u_zeit}]
            
        return res # Wir geben die komplette Liste für die Stunde zurück
    except Exception as e:
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:10], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('leipzig_hbf.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
