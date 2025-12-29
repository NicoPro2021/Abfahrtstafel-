import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 1. ID für Rodleben suchen (IBNR 8010298)
        suche_url = "https://v6.db.transport.rest/locations?query=Rodleben&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return []
        
        station_id = suche_data[0]['id']
        
        # 2. Abfahrten laden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=15&remarks=true"
        r = requests.get(url, timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                # Nur Züge (RE/RB), keine Busse
                if line.get('product') in ['bus', 'tram']: continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeit-Berechnung für die Minuten-Anzeige
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # DEINE LOGIK: +Minuten bei Verspätung, sonst leer
                info_feld = ""
                if d.get('cancelled'):
                    info_feld = "FÄLLT AUS"
                elif diff > 0:
                    info_feld = f"+{diff}"

                # Grund/Hinweis finden
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
            
        return res[:10]
    except:
        return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('rodleben.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
