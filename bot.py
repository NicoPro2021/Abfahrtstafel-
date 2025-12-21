import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Wir probieren nacheinander diese IDs für Zerbst/Anhalt
    ids_to_try = ["8006654", "8010404"]
    fahrplan = []

    # 1. Versuch über IRIS (XML)
    for eva in ids_to_try:
        for i in range(3): # 3 Stunden scannen
            t = jetzt + timedelta(hours=i)
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    for s in root.findall('s'):
                        dp = s.find('dp')
                        tl = s.find('tl')
                        if dp is not None and tl is not None:
                            zug = f"{tl.get('c', '')}{tl.get('n', '') or tl.get('l', '')}"
                            if "RT" in zug: continue # Kassel-Filter
                            
                            p_zeit = dp.get('pt')[-4:]
                            zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                            
                            if i == 0 and zeit_str < u_zeit: continue
                            
                            ziel = dp.get('ppth', '').split('|')[-1][:18]
                            fahrplan.append({"zeit": zeit_str, "linie": zug, "ziel": ziel, "info": "pünktlich"})
            except: continue
        if fahrplan: break # Wenn wir Daten haben, stoppen wir hier

    # 2. Backup-Versuch über HAFAS (falls IRIS leer war)
    if not fahrplan:
        try:
            h_url = "https://v6.db.transport.rest/stops/8006654/departures?duration=120&results=10"
            r = requests.get(h_url, timeout=10)
            if r.status_code == 200:
                for dep in r.json().get('departures', []):
                    line = dep.get('line', {}).get('name', '').replace(" ", "")
                    if "RT" in line: continue
                    w = dep.get('when') or dep.get('plannedWhen', '')
                    zeit_str = w.split('T')[1][:5]
                    fahrplan.append({"zeit": zeit_str, "linie": line, "ziel": dep.get('direction', '')[:18], "info": "pünktlich"})
        except: pass

    fahrplan.sort(key=lambda x: x['zeit'])
    # Duplikate entfernen
    seen = set()
    final = []
    for f in fahrplan:
        if f['zeit'] not in seen:
            final.append(f)
            seen.add(f['zeit'])
    
    return final[:10] if final else [{"zeit": u_zeit, "linie": "INFO", "ziel": "Kein Zug gef.", "info": "Check ID"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
