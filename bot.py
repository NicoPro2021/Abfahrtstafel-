import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Wir nehmen einfach die aktuelle Stunde und die nächste
    jetzt = datetime.now(timezone.utc) + timedelta(hours=1)
    eva = "8006654"
    fahrplan = []

    for i in range(2):
        t = jetzt + timedelta(hours=i)
        url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{t.strftime('%y%m%d')}/{t.strftime('%H')}"
        
        try:
            r = requests.get(url, timeout=10)
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp')
                tl = s.find('tl')
                if dp is not None and tl is not None:
                    # Wir speichern ALLES, ohne Filterung
                    fahrplan.append({
                        "zeit": dp.get('pt')[-4:],
                        "linie": tl.get('c', '') + (tl.get('n', '') or ""),
                        "ziel": dp.get('ppth', '').split('|')[-1][:15],
                        "info": "OK"
                    })
        except:
            continue

    return fahrplan

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=4)
