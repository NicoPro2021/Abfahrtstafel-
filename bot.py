import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime

def hole_daten():
    jetzt = datetime.now()
    datum = jetzt.strftime("%y%m%d")
    stunde = jetzt.strftime("%H")
    u_zeit = jetzt.strftime("%H:%M")
    
    # ID für Zerbst/Anhalt: 8006654
    # 1. Geplante Züge (Timetable)
    plan_url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/8006654/{datum}/{stunde}"
    # 2. Echtzeit-Änderungen (Verspätungen & Gründe)
    fchg_url = "https://iris.noncd.db.de/iris-tts/timetable/fchg/8006654"
    
    try:
        # Plandaten laden
        r_p = requests.get(plan_url, timeout=15)
        root_p = ET.fromstring(r_p.content)
        
        # Echtzeitdaten laden
        r_f = requests.get(fchg_url, timeout=15)
        root_f = ET.fromstring(r_f.content)
        
        # Echtzeit-Infos in ein Dictionary packen
        changes = {}
        for s in root_f.findall('s'):
            s_id = s.get('id')
            ar = s.find('ar')
            if ar is not None:
                ct = ar.get('ct') # neue Zeit
                # Grund suchen (Nachricht)
                msg = ""
                for m in ar.findall('m'):
                    if m.get('cat') in ['f', 'd']: # 'f' sind oft Störungstexte
                        msg = m.get('c', '') # Code oder Text
                changes[s_id] = {'ct': ct, 'msg': msg}

        fahrplan = []
        for s in root_p.findall('s'):
            s_id = s.get('id')
            dp = s.find('dp') # Departure/Abfahrt
            if dp is not None:
                p_zeit = dp.get('pt')[-4:] # HHMM Format
                zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                
                # Filter: Nur Züge der nächsten Zeit
                linie = f"{dp.get('tl', '')}{dp.get('l', '')}"
                ziel = dp.get('ppth', '').split('|')[-1] # Letzter Halt
                gleis = dp.get('pp', '-')
                
                # Echtzeit-Info zuordnen
                info = "pünktlich"
                if s_id in changes:
                    c = changes[s_id]
                    if c['ct']:
                        # Verspätung berechnen
                        diff = (datetime.strptime(c['ct'][-4:], "%H%M") - 
                                datetime.strptime(p_zeit, "%H%M")).seconds // 60
                        info = f"+{diff}" if diff > 0 else "pünktlich"
                    if c['msg']:
                        # Hier kann man Codes in Text umwandeln, z.B. 80 -> "Bauarbeiten"
                        info += f" (Code {c['msg']})"

                fahrplan.append({
                    "zeit": zeit_str,
                    "linie": linie,
                    "ziel": ziel[:18],
                    "gleis": gleis,
                    "info": info,
                    "update": u_zeit
                })

        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:6] if fahrplan else [{"zeit": "Noch", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": u_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "IRIS", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
