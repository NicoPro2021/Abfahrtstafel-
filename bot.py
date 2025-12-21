import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt = datetime.now()
    update_zeit = jetzt.strftime("%H:%M")
    
    # Exakte Koordinaten Bahnhof Zerbst/Anhalt
    LAT = "51.960"
    LON = "12.083"
    
    try:
        # Schritt 1: Finde die Abfahrten direkt über GPS-Koordinaten
        url = f"https://v5.db.transport.rest/stops/nearby?latitude={LAT}&longitude={LON}&results=1&distance=500"
        stations = requests.get(url, verify=False, timeout=15).json()
        
        if not stations:
            return [{"zeit": "Err", "linie": "GPS", "ziel": "Ort nicht gef.", "gleis": "-", "info": update_zeit}]
        
        # Die erste gefundene Station nehmen (sollte Zerbst sein)
        station_id = stations[0]['id']
        
        # Schritt 2: Abfahrten mit Verspätungsgründen (remarks) laden
        dep_url = f"https://v5.db.transport.rest/stops/{station_id}/departures?duration=120&remarks=true&results=10"
        response = requests.get(f"{dep_url}&t={int(jetzt.timestamp())}", verify=False, timeout=15)
        
        data = response.json()
        departures = data if isinstance(data, list) else data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # WICHTIG: Erneuter Filter gegen Kassel-Fehlleitungen
            if "RT" in linie or "Kassel" in dep.get('direction', ''):
                continue

            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- Verspätungsgründe (Remarks) ---
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            wichtige_info = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    wichtige_info = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                minuten = f"+{int(delay/60)}"
                info_text = f"{minuten} {wichtige_info}".strip()
            elif wichtige_info:
                info_text = wichtige_info

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:40],
                "update": update_zeit
            })

        if not fahrplan:
            return [{"zeit": "Check", "linie": "DB", "ziel": "Suche RE13...", "gleis": "-", "info": update_zeit}]

        return fahrplan[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "-", "info": update_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
