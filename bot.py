import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitkorrektur Deutschland
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Zerbst/Anhalt offizielle EVA-Nummer
    eva = "8006654" 
    fahrplan = []
    
    # Zerbst-Relevante Linien (RE13 nach Magdeburg/Leipzig, RB42 nach Dessau/Magdeburg)
    erlaubte_linien = ["RE13", "RB42"]

    try:
        for i in range(4): # 4 Stunden scannen
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                if dp is not None and tl is not None:
                    # Typ (RE/RB) + Nummer (13/42)
                    typ = tl.get('c', '')
                    nr = tl.get('n', '') or tl.get('l', '')
                    zug_name = f"{typ}{nr}"
                    
                    # FILTER: Nur RE13 und RB42 durchlassen!
                    # Das verhindert, dass Berlin- oder Kassel-Züge in die Liste rutschen
                    if not any(x in zug_name for x in erlaubte_linien):
                        continue
                    
                    raw_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{raw_zeit[:2]}:{raw_zeit[2:]}"
                    
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

    # Sortieren nach Uhrzeit
    fahrplan.sort(key=lambda x: x['zeit'])
    return fahrplan[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
