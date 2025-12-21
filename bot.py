import requests
import json
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir nutzen jetzt die stabile HAFAS-Schnittstelle von Jurebus (sehr zuverlässig für DB)
URL = "https://db.jurebus.de/api/v1/station/8006654/departures"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Maximal 3 Versuche bei einem 503 Fehler
    for i in range(3):
        try:
            response = requests.get(URL, headers=headers, timeout=20, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                fahrplan = []

                # Die Struktur dieser API ist sehr einfach (Liste von Zügen)
                for dep in data[:6]:
                    fahrplan.append({
                        "zeit": dep.get('time', '--:--'),
                        "linie": dep.get('train', '???').replace(" ", ""),
                        "ziel": dep.get('destination', 'Unbekannt')[:18],
                        "gleis": str(dep.get('platform', '-')),
                        "info": dep.get('delay', '')
                    })
                return fahrplan

            if response.status_code == 503:
                print(f"Server überlastet (503), Versuch {i+1} von 3...")
                time.sleep(5) # Kurz warten vor Neustart
                continue

            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        except Exception as e:
            return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]
            
    return [{"zeit": "Err", "linie": "DB", "ziel": "503-Timeout", "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Update beendet.")
