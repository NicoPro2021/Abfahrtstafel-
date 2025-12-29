import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    # FESTE ID FÜR ZERBST/ANHALT (Sachsen-Anhalt)
    # Verhindert Irrläufer nach Zella-Mehlis oder Bad Belzig
    station_id = "8010404" 
    
    try:
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=480&results=15&remarks=true"
        r_raw = requests.get(url, timeout=15)
        r_raw.raise_for_status()
        r = r_raw.json()
        
        res = []
        for d in r.get('departures', []):
            # 1. Filter: Keine Busse
            if d.get('line', {}).get('product') == 'bus': 
                continue
            
            # 2. Sicherheits-Check: Zeitdaten vorhanden?
            soll_raw = d.get('plannedWhen')
            ist_raw = d.get('when') or soll_raw
            
            if not soll_raw: # Wenn gar keine Zeit da ist, überspringen
                continue

            # 3. Zeit sicher verarbeiten
            try:
                soll_zeit = soll_raw.split('T')[1][:5]
                ist_zeit = ist_raw.split('T')[1][:5]
            except (AttributeError, IndexError):
                continue

            # 4. Grund / Verspätungstext finden
            remarks = d.get('remarks', [])
            grund = ""
            if isinstance(remarks, list):
                for rm in remarks:
                    if rm.get('type') == 'hint':
                        t = rm.get('text', '').strip()
                        # Unwichtige Infos filtern
                        if t and "Fahrrad" not in t and "WLAN" not in t:
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
        # Fehlermeldung als JSON-Eintrag, damit die Webseite nicht leer bleibt
        return [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15], "grund": "Check Logs"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('zerbst.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
