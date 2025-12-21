import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitkorrektur: GitHub läuft auf UTC, wir addieren 1 Stunde für Deutschland (Winterzeit)
    jetzt_berlin = datetime.now(timezone.utc) + timedelta(hours=1)
    u_zeit = jetzt_berlin.strftime("%H:%M")
    
    # DB Station ID für Zerbst: 8006654
    eva = "8006654"
    fahrplan = []
    
    try:
        # Wir laden die nächsten 3 Stunden, um eine volle Liste zu bekommen
        for i in range(3):
            stunde_obj = jetzt_berlin + timedelta(hours=i)
            datum = stunde_obj.strftime("%y%m%d")
            stunde = stunde_obj.strftime("%H")
            
            # Offizielle IRIS-Schnittstelle der Deutschen Bahn
            url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
            r = requests.get(url, timeout=15)
            
            if r.status_code != 200:
                continue
            
            root = ET.fromstring(r.content)
            
            for s in root.findall('s'):
                tl = s.find('tl') # Train Line (Typ und Nummer)
                dp = s.find('dp') # Departure (Abfahrt)
                
                if tl is not None and dp is not None:
                    # Filter: Nur Regionalzüge (RE und RB)
                    zugtyp = tl.get('c', '')
                    if zugtyp not in ['RE', 'RB']:
                        continue
                    
                    # Geplante Abfahrtszeit (Format: YYMMDDHHMM, wir brauchen nur HH:MM)
                    p_zeit = dp.get('pt')[-4:] 
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Vergangene Züge der aktuellen Stunde ignorieren
                    if i == 0 and zeit_str < u_zeit:
                        continue
                    
                    # Linie zusammenbauen (z.B. RE13)
                    linie = f"{zugtyp}{tl.get('n', '') or tl.get('l', '')}"
                    
                    # Ziel extrahieren (letzter Halt im Fahrtverlauf)
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel unbekannt"
                    
                    # Gleis extrahieren
                    gleis = dp.get('pp', '-')
                    
                    fahrplan.append({
                        "zeit": zeit_str,
                        "linie": linie,
                        "ziel": ziel[:18], # Kürzen für das Display
                        "gleis": gleis,
                        "info": "planmäßig",
                        "update": u_zeit
                    })
                    
    except Exception as e:
        # Fehler-Objekt für das JSON, falls etwas schiefgeht
        return [{"zeit": "Err", "linie": "API", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

    # Die Liste nach der Uhrzeit sortieren
    fahrplan.sort(key=lambda x: x['zeit'])
    
    # Duplikate entfernen (Züge stehen manchmal in zwei Stunden-Slots)
    eindeutige_liste = []
    gesehen = set()
    for f in fahrplan:
        key = f"{f['zeit']}{f['linie']}"
        if key not in gesehen:
            eindeutige_liste.append(f)
            gesehen.add(key)

    # Wir geben die nächsten 10 Verbindungen zurück
    return eindeutige_liste[:10]

if __name__ == "__main__":
    daten = hole_daten()
    # Speichern als daten.json für den ESP32
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
