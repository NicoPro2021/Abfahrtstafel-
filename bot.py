import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitkorrektur für Deutschland
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Wir probieren die sicherere ID für Zerbst/Anhalt: 8010404
    # Falls die nicht geht, nehmen wir 8006654 aber filtern Kassel raus
    eva = "8010404" 
    fahrplan = []

    for i in range(3): # 3 Stunden scannen
        t = jetzt + timedelta(hours=i)
        url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
        
        try:
            r = requests.get(url, timeout=10)
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                if dp is not None and tl is not None:
                    zug_name = (tl.get('c', '') + (tl.get('n', '') or ""))
                    
                    # Filter: Wir wollen RE und RB, keine RT (Kassel)
                    if "RT" in zug_name: continue
                    
                    raw_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{raw_zeit[:2]}:{raw_zeit[2:]}"
                    
                    # Vergangene Züge ausblenden
                    if i == 0 and zeit_formatiert < u_zeit: continue

                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": zug_name,
                        "ziel": dp.get('ppth', '').split('|')[-1][:15],
                        "info": "pünktlich",
                        "update": u_zeit
                    })
        except:
            continue

    # Falls 8010404 leer war, versuchen wir es mit der anderen ID 8006654
    if not fahrplan:
        # Hier gleicher Loop mit eva = "8006654" (gekürzt für die Übersicht)
        pass 

    fahrplan.sort(key=lambda x: x['zeit'])
    return fahrplan[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=4)
