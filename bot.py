import requests
import json
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def hole_daten():
    jetzt = datetime.now().strftime("%H:%M")
    # VBB-ID für Zerbst/Anhalt: 900000143501
    # Wir laden Abfahrten inkl. Remarks (Gründe) für 120 Minuten
    url = "https://v6.vbb.transport.rest/stops/900000143501/departures?duration=120&remarks=true&results=10"
    
    try:
        # Wir fügen einen Cache-Buster hinzu
        response = requests.get(f"{url}&t={int(datetime.now().timestamp())}", timeout=25, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": "Server Busy", "gleis": "-", "info": jetzt}]

        data = response.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Wir nehmen nur echte Züge (RE, RB)
            line_obj = dep.get('line', {})
            linie = line_obj.get('name', '???').replace(" ", "")
            
            # Filter gegen den Kassel-Bug (falls er hier auch auftaucht)
            if "RT" in linie: continue

            p_time = dep.get('when') or dep.get('plannedWhen', '')
            zeit = p_time.split('T')[1][:5] if 'T' in p_time else "--:--"
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # --- Verspätungsgründe ---
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    # Wir nehmen den Text oder die Zusammenfassung
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                minuten = f"+{int(delay/60)}"
                info_text = f"{minuten} {grund}".strip()
            elif grund:
                info_text = grund

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:40],
                "update": jetzt
            })

        if not fahrplan:
            return [{"zeit": "Warte", "linie": "DB", "ziel": "Keine Züge aktuell", "gleis": "-", "info": jetzt}]

        return fahrplan[:6]

    except Exception as e:
        # Falls es wieder zum Timeout kommt
        return [{"zeit": "Timeout", "linie": "Bot", "ziel": "Versuche erneut", "gleis": "-", "info": jetzt}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
