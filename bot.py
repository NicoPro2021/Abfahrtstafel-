import requests
import json
import urllib3

# Schaltet die SSL-Warnungen aus
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Zerbst/Anhalt ID
STATION_ID = "8006654"
# Eine sehr stabile Schnittstelle für DB-Daten
URL = f"https://v5.db.transport.rest/stops/{STATION_ID}/departures?duration=120&results=10"

def hole_daten():
    try:
        # verify=False schaltet den SSL-Check aus, der vorhin zum Error führte
        response = requests.get(URL, timeout=20, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        data = response.json()
        # In dieser API liegen die Daten direkt in einer Liste oder unter 'departures'
        departures = data.get('departures', data) if isinstance(data, dict) else data
        
        fahrplan = []

        for dep in departures:
            # Zeit holen und formatieren
            zeit_raw = dep.get('when') or dep.get('plannedWhen')
            zeit = zeit_raw.split('T')[1][:5] if zeit_raw and 'T' in zeit_raw else "--:--"
            
            # Linie (z.B. RE13)
            line_info = dep.get('line', {})
            linie = line_info.get('name', '???')
            
            # Ziel
            ziel = dep.get('direction', 'Unbekannt')
            
            # Gleis
            gleis = dep.get('platform') or "-"
            
            # Verspätung
            info = ""
            delay = dep.get('delay')
            if delay is not None:
                info = f"+{int(delay/60)}" if delay > 0 else "pünktlich"

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel[:18],
                "gleis": str(gleis),
                "info": info
            })

        if not fahrplan:
            return [{"zeit": "00:00", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": ""}]
            
        return fahrplan[:6]

    except Exception as e:
        # Zeigt uns genau, was schief läuft
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Daten-Update beendet.")
