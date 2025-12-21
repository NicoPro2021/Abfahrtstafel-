import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Deutsche Zeit berechnen
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Zerbst/Anhalt ID
    eva = "8006654" 
    fahrplan = []

    try:
        # Wir scannen 5 Stunden, um eine volle Liste zu bekommen
        for i in range(5):
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            
            r = requests.get(url, timeout=12)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                
                if dp is not None and tl is not None:
                    # Wir bauen den Liniennamen dynamisch
                    typ = tl.get('c', '') # RE, RB, etc.
                    nr = tl.get('n', '') or tl.get('l', '')
                    zug_name = f"{typ}{nr}"
                    
                    # FILTER: 
                    # 1. Keine RegioTrams aus Kassel (RT)
                    # 2. Keine ICE/IC (da diese selten direkt in Zerbst halten)
                    if "RT" in zug_name or "ICE" in zug_name:
                        continue
                        
                    raw_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{raw_zeit[:2]}:{raw_zeit[2:]}"
                    
                    # Nur zukünftige Züge anzeigen
                    if i == 0 and zeit_formatiert < u_zeit:
                        continue

                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel"

                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": zug_name,
                        "ziel": ziel[:18],
                        "info": "pünktlich",
                        "update": u_zeit
                    })
    except Exception as e:
        print(f"Fehler: {e}")

    # Sortieren nach Uhrzeit
    fahrplan.sort(key=lambda x: x['zeit'])
    
    # Duplikate entfernen
    final = []
    check = set()
    for f in fahrplan:
        if f['zeit'] not in check:
            final.append(f)
            check.add(f['zeit'])

    return final[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
