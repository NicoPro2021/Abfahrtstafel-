import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # ID 8010405 = Zerbst/Anhalt (Sachsen-Anhalt)
    station_id = "8010405" 
    
    try:
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=20&remarks=true"
        r_raw = requests.get(url, timeout=15)
        r_raw.raise_for_status()
        data = r_raw.json()
        
        departures = data.get('departures', [])
        res = []
        
        for d in departures:
            try:
                line = d.get('line')
                if not line or line.get('product') == 'bus': continue
                
                # Filter: Nur Züge der Region (RE13, RE14, RB51)
                name = line.get('name', '').replace(" ", "")
                # Falls wir wieder woanders landen, blocken wir Thüringer Ziele
                ziel = d.get('direction', 'Unbekannt')
                if any(x in ziel for x in ["Erfurt", "Würzburg", "Meiningen"]): continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeitberechnung für Minuten
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # DEINE LOGIK: +Minuten oder LEER
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
