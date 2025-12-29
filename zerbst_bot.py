import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # Wir nutzen die ID 8010405, aber mit einer eingebauten "Berlin-Sperre"
    url = "https://v6.db.transport.rest/stops/8010405/departures?duration=480&results=50&remarks=true"
    
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
                ziel = d.get('direction', '')

                # --- DER BERLIN-BLOCKER ---
                # Wenn diese Begriffe auftauchen, sind wir im falschen Bundesland:
                falsche_ziele = ["Ahrensfelde", "Potsdam", "Wannsee", "Frankfurt(Oder)", "Oranienburg", "Rudow", "Cottbus"]
                if any(stadt in ziel for stadt in falsche_ziele):
                    continue
                
                # In Zerbst fahren nur RE13, RE14 oder RB51
                if not any(x in name for x in ["RE13", "RE14", "RB51"]):
                    continue

                # Zeitberechnung für deine Minuten-Anzeige
                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

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
                    "ziel": ziel[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info_feld, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
            
        return res[:10]
    except:
        return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
