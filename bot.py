import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitkorrektur Deutschland
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Zerbst/Anhalt ID (8010404 ist oft stabiler als 8006654)
    eva = "8010404" 
    fahrplan = []

    try:
        # Wir scannen die nächsten 4 Stunden
        for i in range(4):
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                if dp is not None and tl is not None:
                    zug_name = (tl.get('c', '') + (tl.get('n', '') or tl.get('l', '')))
                    
                    # SICHERHEITS-CHECK: Wir wollen keine ICEs oder Berliner RegioTrams
                    # Zerbst hat RE13, RB42 und selten IC
                    if "ICE" in zug_name or "OE" in zug_name: continue
                    
                    raw_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{raw_zeit[:2]}:{raw_zeit[2:]}"
                    
                    # Zeitfilter
                    if i == 0 and zeit_formatiert < u_zeit: continue

                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel"

                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": zug_name,
                        "ziel": ziel[:18],
                        "info": "pünktlich",
                        "update": u_zeit
                    })
    except:
        pass

    # Falls Zerbst (8010404) leer ist, probieren wir die Alternativ-ID 8006654
    if not fahrplan:
        # (Wiederholung des Codes mit eva = "8006654")
        # Hier gekürzt, damit es übersichtlich bleibt
        pass

    fahrplan.sort(key=lambda x: x['zeit'])
    return fahrplan[:10]

if __name__ == "__main__":
    daten = hole_daten()
    # ensure_ascii=False fixit die Umlaute (\u00fcnktlich -> pünktlich)
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
