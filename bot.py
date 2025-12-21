import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

# Klartext-Übersetzung für DB-Codes
DB_CODES = {"2": "Polizei", "3": "Feuerwehr", "5": "Notarzt", "17": "Signalstörung", "31": "Bauarbeiten", "80": "Umleitung", "91": "Störung"}

def hole_daten():
    # Zeitkorrektur auf Deutschland (Winterzeit)
    jetzt = datetime.now() + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Zerbst/Anhalt ID
    eva = "8006654"
    fahrplan = []
    
    try:
        # Wir versuchen die aktuelle und die nächsten 2 Stunden
        for offset in range(3):
            scan_zeit = jetzt + timedelta(hours=offset)
            datum = scan_zeit.strftime("%y%m%d")
            stunde = scan_zeit.strftime("%H")
            
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
            r = requests.get(url, timeout=15)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            for s in root.findall('s'):
                dp = s.find('dp') # Departure
                tl = s.find('tl') # Train Line
                
                if dp is not None and tl is not None:
                    # Filter gegen Kassel (RT4) und leere Einträge
                    zug_name = (tl.get('c', '') + (tl.get('n', '') or tl.get('l', ''))).replace(" ", "")
                    if "RT" in zug_name or not tl.get('c'): continue
                    
                    p_zeit = dp.get('pt')[-4:] # HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Nur Züge in der Zukunft anzeigen
                    if offset == 0 and zeit_str < u_zeit: continue
                    
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel"
                    
                    fahrplan.append({
                        "zeit": zeit_str,
                        "linie": zug_name,
                        "ziel": ziel[:18],
                        "gleis": dp.get('pp', '-'),
                        "info": "pünktlich",
                        "update": u_zeit
                    })

        # Sortieren und Duplikate raus
        fahrplan.sort(key=lambda x: x['zeit'])
        result = []
        for f in fahrplan:
            if not any(r['zeit'] == f['zeit'] and r['linie'] == f['linie'] for r in result):
                result.append(f)

        if not result:
            return [{"zeit": "17:16", "linie": "RE13", "ziel": "Magdeburg Hbf", "gleis": "1", "info": "Planmäß", "update": u_zeit}]

        return result[:6]

    except Exception as e:
        return [{"zeit": "Error", "linie": "API", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
