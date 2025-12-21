import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import pytz # Für die korrekte Zeitzone

def hole_daten():
    # Zeitzone explizit auf Deutschland setzen
    tz = pytz.timezone('Europe/Berlin')
    jetzt_berlin = datetime.now(tz)
    u_zeit = jetzt_berlin.strftime("%H:%M")
    
    # DB Station ID für Zerbst: 8006654
    eva = "8006654"
    fahrplan = []
    
    try:
        # Wir laden die nächsten 3 Stunden für eine volle Liste
        for i in range(3):
            stunde_obj = jetzt_berlin + timedelta(hours=i)
            datum = stunde_obj.strftime("%y%m%d")
            stunde = stunde_obj.strftime("%H")
            
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
            r = requests.get(url, timeout=15)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                tl = s.find('tl')
                dp = s.find('dp')
                
                if tl is not None and dp is not None:
                    # Nur Regionalzüge
                    zugtyp = tl.get('c', '')
                    if zugtyp not in ['RE', 'RB']: continue
                    
                    p_zeit = dp.get('pt')[-4:] # HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Filter: Nur Züge, die JETZT oder später fahren
                    if i == 0 and zeit_str < u_zeit: continue
                    
                    linie = f"{zugtyp}{tl.get('n', '') or tl.get('l', '')}"
                    # Ziel extrahieren
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
    except Exception as e:
        return [{"zeit": "Err", "linie": "API", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

    fahrplan.sort(key=lambda x: x['zeit'])
    
    # Duplikate entfernen
    eindeutig = []
    gesehen = set()
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
