import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    # Wir probieren zwei verschiedene Schnittstellen-Server
    urls = [
        "https://v6.db.transport.rest/stops/8006654/departures?duration=300&results=15&remarks=true",
        "https://v6.vbb.transport.rest/stops/900000143501/departures?duration=300&results=15&remarks=true"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    raw_deps = []
    erfolg = False

    for url in urls:
        try:
            res = requests.get(f"{url}&t={int(datetime.now().timestamp())}", headers=headers, timeout=15, verify=False)
            if res.status_code == 200:
                data = res.json()
                raw_deps = data if isinstance(data, list) else data.get('departures', [])
                if len(raw_deps) > 0:
                    erfolg = True
                    break # Erste funktionierende Quelle nehmen
        except:
            continue

    if not erfolg:
        return [{"zeit": "Offline", "linie": "RE13", "ziel": "Pruefe WLAN", "gleis": "-", "info": u_zeit}]

    fahrplan = []
    for dep in raw_deps:
        linie = dep.get('line', {}).get('name', '???').replace(" ", "")
        if "RT" in linie: continue # Kassel-Filter

        w = dep.get('when') or dep.get('plannedWhen', '')
        zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
        ziel = dep.get('direction', 'Unbekannt')[:18]
        gleis = str(dep.get('platform') or "-")
        
        # Verspätung & Info
        delay = dep.get('delay')
        remarks = dep.get('remarks', [])
        grund = next((r.get('summary') or r.get('text', '') for r in remarks if r.get('type') == 'warning'), "")
        
        info_text = "pünktlich"
        if delay and delay > 0:
            info_text = f"+{int(delay/60)} {grund}".strip()
        elif grund:
            info_text = grund

        fahrplan.append({
            "zeit": zeit, "linie": linie, "ziel": ziel, 
            "gleis": gleis, "info": info_text[:35], "update": u_zeit
        })

    fahrplan.sort(key=lambda x: x['zeit'])
    return fahrplan[:10] # Top 10 Züge

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
