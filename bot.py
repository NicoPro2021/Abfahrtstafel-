import requests
import json

# Zerbst/Anhalt hat die Stations-ID 8006654
STATION_ID = "8006654"
# Eine öffentliche HAFAS-Schnittstelle (vbb ist sehr stabil)
URL = f"https://v5.vbb.transport.rest/stops/{STATION_ID}/departures?duration=60&results=10"

def hole_daten():
    try:
        response = requests.get(URL, timeout=15)
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        fahrplan = []

        for dep in data:
            # Zeit formatieren (kommt als 2024-05-24T14:30:00)
            zeit_voll = dep.get('when', dep.get('plannedWhen', ''))
            zeit = zeit_voll.split('T')[1][:5] if 'T' in zeit_voll else "--:--"
            
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???')
            
            # Ziel
            ziel = dep.get('direction', 'Unbekannt')
            
            # Gleis
            gleis = dep.get('platform', '-')
            
            # Verspätung berechnen
            info = ""
            delay = dep.get('delay')
            if delay is not None:
                if delay > 0:
                    info = f"+{int(delay/60)}"
                elif delay == 0:
                    info = "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:20],
                "gleis": gleis,
                "info": info
            })

        return fahrplan[:6] if fahrplan else [{"zeit": "Kein", "linie": "ZUG", "ziel": "Gefunden", "gleis": "", "info": ""}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("HAFAS-Update erfolgreich!")
