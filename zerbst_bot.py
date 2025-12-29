import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # Wir nutzen eine alternative, extrem stabile API-Route für Zerbst (IBNR 8010405)
    url = "https://v6.db.transport.rest/stops/8010405/departures?duration=600&results=20&linesOfStops=true&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                name = line.get('name', '').replace(" ", "")
                
                # Wir filtern nur Busse aus. Alles andere (RE13, RE14, RB51) lassen wir zu.
                if line.get('product') == 'bus': continue

                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeitberechnung
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                
                # Deine Logik: +Minuten oder leer
                info_feld = ""
                if d.get('cancelled'):
                    info_feld = "FÄLLT AUS"
                elif diff > 0:
                    info_feld = f"+{diff}"

                res.append({
                    "zeit": soll_dt.strftime("%H:%M"), 
                    "echte_zeit": ist_dt.strftime("%H:%M"), 
                    "linie": name, 
                    "ziel": d.get('direction', 'Ziel')[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info_feld, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
            
        # Wenn immer noch leer, schreiben wir einen Test-Eintrag zur Diagnose
        if not res:
            res = [{"zeit": "---", "linie": "RE13/14", "ziel": "Keine Züge aktuell", "gleis": "-", "info": "", "update": u_zeit}]

        return res[:10]
    except Exception as e:
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
