import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # ID für Biederitz suchen (Knotenpunkt Richtung Magdeburg/Dessau/Berlin)
        suche_url = "https://v6.db.transport.rest/locations?query=Biederitz&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return []
        
        station_id = suche_data[0]['id']
        
        # Abfahrten laden (duration=480 Minuten für weiten Vorblick)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=15&remarks=true"
        r = requests.get(url, timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Wir lassen BUSSE jetzt drin (Wichtig für SEV), aber filtern Trams (falls vorhanden)
                if line.get('product') == 'tram': continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeit-Berechnung für die "+Minuten" Logik
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # INFO: Minuten bei Verspätung, sonst leer
                info_feld = ""
                if d.get('cancelled'):
                    info_feld = "FÄLLT AUS"
                elif diff > 0:
                    info_feld = f"+{diff}"

                # Grund/Hinweis extrahieren (Besonders wichtig bei Anschluss-Knoten)
                remarks = d.get('remarks', [])
                grund = ""
                for rm in remarks:
                    if rm.get('type') == 'hint':
                        t = rm.get('text', '').strip()
                        if t and "Fahrrad" not in t and "WLAN" not in t:
                            grund = t
                            break

                res.append({
                    "zeit": soll_dt.strftime("%H:%M"), 
                    "echte_zeit": ist_dt.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', 'Ziel')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info_feld, 
                    "grund": grund,
                    "update": u_zeit
                })
            except: continue
            
        return res[:12]
    except:
        return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('biederitz.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
