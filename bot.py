import requests
import json
import urllib3
import time
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    # Zerbst/Anhalt ID (VBB/DB kompatibel)
    STATION_ID = "8006654"
    # Wir nutzen den VBB-Endpunkt, da dieser oft stabiler ist als der DB-Endpunkt
    url = f"https://v6.vbb.transport.rest/stops/{STATION_ID}/departures?results=10&duration=120"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # Maximal 3 Versuche
    for versuch in range(3):
        try:
            # Cache-Buster um alte Daten zu vermeiden
            t_url = f"{url}&t={int(datetime.now().timestamp())}"
            response = requests.get(t_url, headers=headers, timeout=20, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                departures = data.get('departures', [])
                
                fahrplan = []
                update_zeit = datetime.now().strftime("%H:%M")

                for dep in departures:
                    linie = dep.get('line', {}).get('name', '???')
                    # Wir filtern die Testdaten aus Kassel (RT4) hart aus
                    if "RT" in linie: continue

                    w = dep.get('when') or dep.get('plannedWhen', '')
                    zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
                    ziel = dep.get('direction', 'Unbekannt')
                    gleis = str(dep.get('platform') or "-")
                    
                    delay = dep.get('delay')
                    info = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

                    fahrplan.append({
                        "zeit": zeit,
                        "linie": linie.replace(" ", ""),
                        "ziel": ziel[:18],
                        "gleis": gleis,
                        "info": info,
                        "update": update_zeit
                    })
                
                return fahrplan[:6] if fahrplan else [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": update_zeit}]

            if response.status_code == 503:
                print(f"Server beschäftigt (503)... Versuch {versuch + 1}...")
                time.sleep(5) # 5 Sekunden warten vor dem nächsten Versuch
                continue

            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        except Exception as e:
            if versuch == 2: # Letzter Versuch gescheitert
                return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]
            time.sleep(5)

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
