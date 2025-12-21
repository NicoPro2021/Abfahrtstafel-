import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    jetzt = datetime.now()
    # Deutsche Bahn IRIS Station ID für Zerbst: 8006654
    eva = "8006654"
    
    fahrplan = []
    
    # Wir laden die aktuelle und die nächste Stunde (für mehr Verbindungen)
    for i in range(2):
        stunde_obj = jetzt + timedelta(hours=i)
        datum = stunde_obj.strftime("%y%m%d")
        stunde = stunde_obj.strftime("%H")
        
        url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
        
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                tl = s.find('tl') # Train Line
                dp = s.find('dp') # Departure
                
                if tl is not None and dp is not None:
                    # Filter gegen Kassel-Bug: Nur RE und RB
                    zugtyp = tl.get('c', '')
                    if zugtyp not in ['RE', 'RB']: continue
                    
                    p_zeit = dp.get('pt')[-4:] # Geplante Zeit HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Vergangene Züge ignorieren
                    if i == 0 and zeit_str < u_zeit: continue
                    
                    linie = f"{zugtyp}{tl.get('n', '') or tl.get('l', '')}"
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel unbekannt"
                    
                    fahrplan.append({
                        "zeit": zeit_str,
                        "linie": linie,
                        "ziel": ziel[:18],
                        "gleis": dp.get('pp', '-'),
                        "info": "pünktlich",
                        "update": u_zeit
                    })
        except:
            continue

    # Nach Zeit sortieren
    fahrplan.sort(key=lambda x: x['zeit'])
    
    # Duplikate entfernen (IRIS listet Züge manchmal doppelt)
    gesehen = set()
    eindeutig = []
    for f in fahrplan:
        key = f"{f['zeit']}{f['linie']}"
        if key not in gesehen:
            eindeutig.append(f)
            gesehen.add(key)

    return eindeutig[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
