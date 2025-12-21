import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitkorrektur für Deutschland
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Zerbst/Anhalt ID 8010404 (Sicherer für Zerbst)
    eva = "8010404" 
    fahrplan = []

    try:
        # Wir scannen 3 Stunden, um die Liste voll zu bekommen
        for i in range(3):
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            
            r = requests.get(url, timeout=12)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp') # Departure
                tl = s.find('tl') # Train Line
                
                if dp is not None and tl is not None:
                    # Filter: Nur RE und RB (Kein ICE/Kassel-Müll)
                    zugtyp = tl.get('c', '')
                    if zugtyp not in ['RE', 'RB']: continue
                    
                    linie = f"{zugtyp}{tl.get('n', '') or tl.get('l', '')}"
                    
                    # Zeit formatieren
                    p_zeit = dp.get('pt')[-4:]
                    zeit_formatiert = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Vergangene Züge ausblenden
                    if i == 0 and zeit_formatiert < u_zeit: continue

                    # Ziel und Gleis
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel"
                    gleis = dp.get('pp', '-') # 'pp' ist das geplante Gleis

                    fahrplan.append({
                        "zeit": zeit_formatiert,
                        "linie": linie,
                        "ziel": ziel[:18],
                        "gleis": gleis,
                        "info": "pünktlich",
                        "update": u_zeit
                    })
    except:
        pass

    # Sortieren nach Uhrzeit
    fahrplan.sort(key=lambda x: x['zeit'])
    
    # Falls ID 8010404 leer ist, Backup mit 8006654 (aber Filter auf RE13/RB42)
    if not fahrplan:
        # (Optionaler Backup-Loop hier möglich)
        return [{"zeit": u_zeit, "linie": "INFO", "ziel": "Suche...", "gleis": "-", "info": "Keine Daten"}]

    return fahrplan[:10]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
