import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Wir probieren BEIDE möglichen IDs für Zerbst
    ids = ["8010404", "8006654"] 
    fahrplan = []

    for eva in ids:
        for i in range(3): # 3 Stunden scannen
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code != 200: continue
                root = ET.fromstring(r.content)
                for s in root.findall('s'):
                    dp = s.find('dp')
                    tl = s.find('tl')
                    if dp is not None and tl is not None:
                        # Wir nehmen ALLES was nach Regionalzug aussieht
                        typ = tl.get('c', '')
                        if typ not in ['RE', 'RB']: continue
                        
                        pfad = dp.get('ppth', '').split('|')
                        ziel = pfad[-1] if pfad else ""
                        
                        # FILTER: Nur Züge die in Zerbst-Richtung fahren
                        if not any(z in ziel for z in ["Magdeburg", "Dessau", "Leipzig", "Bitterfeld", "Güterglück"]):
                            continue

                        p_zeit = dp.get('pt')[-4:]
                        zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                        
                        if i == 0 and zeit_str < u_zeit: continue

                        fahrplan.append({
                            "zeit": zeit_str,
                            "linie": f"{typ}{tl.get('n', '') or tl.get('l', '')}",
                            "ziel": ziel[:18],
                            "gleis": dp.get('pp', '-'),
                            "info": "pünktlich"
                        })
            except: continue
        if len(fahrplan) > 0: break # Wenn wir bei der ersten ID was finden, aufhören

    fahrplan.sort(key=lambda x: x['zeit'])
    return fahrplan[:10] if fahrplan else [{"zeit": u_zeit, "linie": "DB", "ziel": "Keine Daten", "gleis": "-", "info": "Retry"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
