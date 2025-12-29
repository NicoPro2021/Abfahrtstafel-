import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 1. Schritt: Wir suchen die ID für Zerbst/Anhalt ganz frisch
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst/Anhalt&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        
        if not suche_data:
            return [{"zeit": "---", "linie": "INFO", "ziel": "Station nicht gef.", "info": ""}]
        
        station_id = suche_data[0]['id']
        
        # 2. Schritt: Abfahrten laden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=20&remarks=true"
        r = requests.get(url, timeout=15).json()
        departures = r.get('departures', [])
        
        res = []
        for d in departures:
            try:
                line = d.get('line', {})
                name = line.get('name', '').replace(" ", "")
                ziel = d.get('direction', '')
                
                # Sicherheits-Filter: Wir blocken S-Bahnen und Berliner Ziele
                if line.get('product') in ['suburban', 'bus']: continue
                if any(stadt in ziel for stadt in ["Ahrensfelde", "Potsdam", "Wannsee"]): continue

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

        # Falls die Liste leer ist, geben wir eine Info-Zeile aus, damit wir wissen was los ist
        if not res:
            res = [{"zeit": "---", "linie": "INFO", "ziel": "Keine Züge aktuell", "info": "", "update": u_zeit}]
            
        return res[:10]
    except Exception as e:
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:10]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
