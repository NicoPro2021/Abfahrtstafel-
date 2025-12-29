import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    try:
        # Wir nutzen die feste ID fuer Zerbst/Anhalt, um Irrläufer zu verhindern
        echte_id = "8010404" 
        
        r_raw = requests.get(f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=15&remarks=true", timeout=15)
        r = r_raw.json()
        
        res = []
        for d in r.get('departures', []):
            # Filter: Nur Züge, keine Busse
            if d.get('line', {}).get('product') == 'bus': continue
            
            # SICHERHEITS-CHECK: Existieren die Zeit-Daten?
            ist_w = d.get('when') or d.get('plannedWhen')
            soll_w = d.get('plannedWhen') or ist_w
            
            if not ist_w or not soll_w: continue # Springe zum nächsten, wenn Zeit fehlt

            # Zeiten sicher schneiden
            soll_zeit = soll_w.split('T')[1][:5]
            ist_zeit = ist_w.split('T')[1][:5]
            
            # Verspätungsgrund finden
            remarks = d.get('remarks', [])
            grund = ""
            for rm in remarks:
                if rm.get('type') == 'hint':
                    t = rm.get('text', '').strip()
                    if t and "Fahrrad" not in t:
                        grund = t
                        break

            info = "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_zeit}" if ist_zeit != soll_zeit else "")
            
            res.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit, 
                "linie": d.get('line', {}).get('name', '???').replace(" ", ""), 
                "ziel": d.get('direction', 'Unbekannt')[:18], 
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                "info": info, 
                "grund": grund,
                "update": u_zeit
            })
            
        return res[:10]
    except Exception as e:
        # Falls gar nichts geht: Fehler-Info fuer die JSON
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
