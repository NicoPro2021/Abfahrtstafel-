import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # Absolute ID für Zerbst/Anhalt
    station_id = "8010404" 
    
    try:
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=15&remarks=true"
        r_raw = requests.get(url, timeout=15)
        r_raw.raise_for_status()
        data = r_raw.json()
        
        departures = data.get('departures', [])
        res = []
        
        for d in departures:
            try:
                line = d.get('line')
                if not line or line.get('product') == 'bus': continue
                
                # Nur RE13, RE14, RB51 (Zerbst-typisch)
                name = line.get('name', '').replace(" ", "")
                if not any(x in name for x in ["RE13", "RE14", "RB51"]): continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeit-Objekte erstellen für die Berechnung der Minuten
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                soll_zeit = soll_dt.strftime("%H:%M")
                ist_zeit = ist_dt.strftime("%H:%M")

                # Logik für das Info-Feld (Verspätung in Minuten oder Leer)
                if d.get('cancelled'):
                    info = "FÄLLT AUS"
                elif diff > 0:
                    info = f"+{diff}" # Schreibt die Verspätungsminuten rein
                else:
                    info = "" # Bleibt leer bei Pünktlichkeit

                res.append({
                    "zeit": soll_zeit, 
                    "echte_zeit": ist_zeit, 
                    "linie": name, 
                    "ziel": d.get('direction', 'Unbekannt')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except:
                continue
            
        return res[:10]

    except Exception as e:
        return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
