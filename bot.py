import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Deutsche Zeit erzwingen (UTC + 1)
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Offizielle ID für Zerbst/Anhalt
    eva = "8006654" 
    fahrplan = []

    try:
        # Wir scannen 4 Stunden-Slots
        for i in range(4):
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp') # Departure
                tl = s.find('tl') # Train Line
                
                if dp is not None and tl is not None:
                    # ZUG-FILTER: Wir lassen NUR RE13 und RB42 durch
                    typ = tl.get('c', '') # RE oder RB
                    nr = tl.get('n', '') or tl.get('l', '') # 13 oder 42
                    zug_name = f"{typ}{nr}"
                    
                    if not any(x in zug_name for x in ["RE13", "RB42"]):
                        continue

                    # Zeit formatieren
                    p_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Zeitfilter: Keine Züge aus der Vergangenheit
                    if i == 0 and zeit_formatiert < u_zeit: continue

                    # Ziel und Gleis extrahieren
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel"
                    gleis = dp.get('pp', '-')

                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": zug_name,
                        "ziel": ziel[:18],
                        "gleis": gleis,
                        "info": "pünktlich",
                        "update": u_zeit
                    })
    except:
        pass

    # Sortieren nach Uhrzeit
    fahrplan.sort(key=lambda x: x['zeit'])
    
    if not fahrplan:
        return [{"zeit": u_zeit, "linie": "INFO", "ziel": "Kein RE13/RB42", "gleis": "-", "info": "Check DB"}]

    return fahrplan[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
