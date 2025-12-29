import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # Geografische Koordinaten von Zerbst/Anhalt Bahnhof
    lat = "51.9599"
    lon = "12.0837"
    
    try:
        # Erst suchen wir die Station per Koordinaten, um die aktuelle Tages-ID zu finden
        suche_url = f"https://v6.db.transport.rest/locations/nearby?latitude={lat}&longitude={lon}&results=1"
        suche_res = requests.get(suche_url, timeout=10).json()
        
        if not suche_res: return []
        echte_id = suche_res[0]['id']
        
        # Jetzt die Abfahrten mit der gefundenen ID
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=15&remarks=true"
        r_raw = requests.get(url, timeout=15)
        r_raw.raise_for_status()
        data = r_raw.json()
        
        departures = data.get('departures', [])
        res = []
        
        for d in departures:
            try:
                line = d.get('line', {})
                if not line or line.get('product') == 'bus': continue
                
                name = line.get('name', '').replace(" ", "")
                
                # Sicherheitscheck gegen Berlin/Thüringen:
                ziel = d.get('direction', '')
                if any(x in ziel for x in ["Berlin", "Würzburg", "Erfurt"]): continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeitberechnung für Minuten
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # DEINE LOGIK: +Minuten oder Leer
                info_feld = ""
                if d.get('cancelled'):
                    info_feld = "FÄLLT AUS"
                elif diff > 0:
                    info_feld = f"+{diff}"

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
            
        return res[:10]
    except: return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
