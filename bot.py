import requests
import json
from datetime import datetime

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    
    # Die stabilste Basis-URL für die DB-Hafas Schnittstelle
    # Zerbst/Anhalt ID: 8006654
    # Wir laden 15 Ergebnisse über 300 Minuten (5 Stunden)
    url = "https://db.transport.rest/stops/8006654/departures?duration=300&results=20&remarks=true"
    
    try:
        # Wir simulieren einen echten Browser, um nicht blockiert zu werden
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'de-DE,de;q=0.9'
        }
        
        # Cache-Buster, damit wir keine alten Daten bekommen
        timestamp = int(datetime.now().timestamp())
        response = requests.get(f"{url}&t={timestamp}", headers=headers, timeout=25)
        
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "DB", "ziel": "Verbindung..", "gleis": "-", "info": u_zeit}]

        data = response.json()
        # Manche Antworten sind direkt Listen, manche haben ein 'departures' Objekt
        raw_deps = data if isinstance(data, list) else data.get('departures', [])
        
        fahrplan = []
        for dep in raw_deps:
            # Linie (z.B. RE13)
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Sicherheits-Filter gegen den Kassel-Bug (RT-Linien)
            if "RT" in linie:
                continue

            # Zeit-Berechnung
            w = dep.get('when') or dep.get('plannedWhen', '')
            zeit = w.split('T')[1][:5] if 'T' in w else "--:--"
            
            ziel = dep.get('direction', 'Unbekannt')[:18]
            gleis = str(dep.get('platform') or "-")
            
            # Verspätung & Text-Info
            delay = dep.get('delay')
            remarks = dep.get('remarks', [])
            
            grund = ""
            for r in remarks:
                if r.get('type') == 'warning':
                    grund = r.get('summary') or r.get('text', '')
                    break
            
            info_text = "pünktlich"
            if delay and delay > 0:
                info_text = f"+{int(delay/60)} {grund}".strip()
            elif grund:
                info_text = grund

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text[:35],
                "update": u_zeit
            })

        # Wenn die Liste leer ist, suchen wir weiter in der Zukunft
        if not fahrplan:
            return [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge aktuell", "gleis": "-", "info": u_zeit}]

        # Sortieren nach Uhrzeit
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:10] # Wir geben die nächsten 10 Verbindungen aus!

    except Exception as e:
        return [{"zeit": "Error", "linie": "Bot", "ziel": "API Offline", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
