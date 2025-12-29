import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # ID für Magdeburg-Herrenkrug
        suche_url = "https://v6.db.transport.rest/locations?query=Magdeburg-Herrenkrug&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return []
        
        station_id = suche_data[0]['id']
        
        # Abfahrten laden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=10&remarks=true"
        r = requests.get(url, timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                if line.get('product') in ['bus', 'tram']: continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                info_feld = "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else "")

                remarks = d.get('remarks', [])
                grund = ""
                for rm in remarks:
                    if rm.get('type') == 'hint':
                        t = rm.get('text', '').strip()
                        if t and "Fahrrad" not in t:
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
            
        return res[:8]
    except:
        return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('magdeburg_herrenkrug.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
