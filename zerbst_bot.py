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
        
        departures = data.get('departures')
        if not isinstance(departures, list):
            return []

        res = []
        for d in departures:
            try:
                # 1. Check: Ist das d-Objekt gültig?
                if not d or not isinstance(d, dict): continue
                
                # 2. Check: Linien-Daten vorhanden?
                line = d.get('line')
                if not line: continue
                if line.get('product') == 'bus': continue
                
                # 3. Check: Zeit-Daten vorhanden?
                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue

                # Zeit sicher formatieren
                soll_zeit = soll_raw.split('T')[1][:5]
                ist_zeit = ist_raw.split('T')[1][:5]
                
                # 4. Check: Linie und Ziel vorhanden?
                name = line.get('name', '???').replace(" ", "")
                ziel = d.get('direction', 'Unbekannt')[:18]
                gleis = str(d.get('platform') or d.get('plannedPlatform') or "-")

                # Grund/Hinweise sicher sammeln
                remarks = d.get('remarks', [])
                grund = ""
                if isinstance(remarks, list):
                    for rm in remarks:
                        if rm.get('type') == 'hint':
                            t = rm.get('text', '').strip()
                            if t and "Fahrrad" not in t and "WLAN" not in t:
                                grund = t
                                break

                info = "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_zeit}" if ist_zeit != soll_zeit else "")
                
                res.append({
                    "zeit": soll_zeit, 
                    "echte_zeit": ist_zeit, 
                    "linie": name, 
                    "ziel": ziel, 
                    "gleis": gleis, 
                    "info": info, 
                    "grund": grund,
                    "update": u_zeit
                })
            except (AttributeError, IndexError, TypeError):
                # Wenn ein einzelner Zug Schrott-Daten hat, einfach ignorieren
                continue
            
        return res[:10]

    except Exception as e:
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15], "grund": "API Problem"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
