import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

def hole_daten():
    # Zeitkorrektur (Winterzeit Deutschland)
    jetzt = datetime.now() + timedelta(hours=1)
    u_zeit = jetzt.strftime("%H:%M")
    
    eva = "8006654" # Zerbst/Anhalt
    fahrplan = []
    
    try:
        # Wir scannen die nächsten 4 Stunden, um sicher zu gehen
        for i in range(4):
            scan_zeit = jetzt + timedelta(hours=i)
            datum = scan_zeit.strftime("%y%m%d")
            stunde = scan_zeit.strftime("%H")
            
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
            r = requests.get(url, timeout=15)
            
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for s in root.findall('s'):
                    dp = s.find('dp') # Departure
                    tl = s.find('tl') # Train Line
                    
                    if dp is not None:
                        # Zeit auslesen
                        p_zeit = dp.get('pt')[-4:] # HHMM
                        zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                        
                        # Züge in der Vergangenheit ignorieren
                        if i == 0 and zeit_str < u_zeit: continue
                        
                        # Linie zusammenbauen (z.B. RE13 oder RB42)
                        linie = ""
                        if tl is not None:
                            linie = (tl.get('c', '') + (tl.get('n', '') or tl.get('l', ''))).replace(" ", "")
                        
                        # Ziel (Letzter Halt im Pfad)
                        pfad = dp.get('ppth', '').split('|')
                        ziel = pfad[-1] if pfad else "Unbekannt"
                        
                        fahrplan.append({
                            "zeit": zeit_str,
                            "linie": linie if linie else "Zug",
                            "ziel": ziel[:18],
                            "gleis": dp.get('pp', '-'),
                            "info": "pünktlich",
                            "update": u_zeit
                        })

        # Sortieren nach Uhrzeit
        fahrplan.sort(key=lambda x: x['zeit'])
        
        # Duplikate entfernen
        final = []
        for f in fahrplan:
            if not any(r['zeit'] == f['zeit'] and r['linie'] == f['linie'] for r in final):
                final.append(f)

        return final[:8] # Bis zu 8 Verbindungen

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Verbindung..", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
