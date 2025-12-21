import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

def hole_daten():
    jetzt = datetime.now()
    stunde = jetzt.strftime("%H")
    datum = jetzt.strftime("%y%m%d")
    update_zeit = jetzt.strftime("%H:%M")
    
    # ID für Zerbst/Anhalt: 8006654
    # Schritt 1: Geplante Daten holen
    plan_url = f"https://iris.noncd.db.de/iris-tts/timetable/plan/8006654/{datum}/{stunde}"
    
    try:
        r_plan = requests.get(plan_url, timeout=15)
        root_plan = ET.fromstring(r_plan.content)
        
        # Schritt 2: Realzeit-Daten (Verspätungen/Gründe) holen
        fchg_url = "https://iris.noncd.db.de/iris-tts/timetable/fchg/8006654"
        r_fchg = requests.get(fchg_url, timeout=15)
        root_fchg = ET.fromstring(r_fchg.content)
        
        # Gründe/Änderungen in Dictionary mappen
        changes = {}
        for s in root_fchg.findall('s'):
            s_id = s.get('id')
            ar = s.find('ar')
            if ar is not None:
                # Zeitänderung (Verspätung)
                ct = ar.get('ct') # Korrigierte Zeit
                # Gründe (Messages)
                msg_text = ""
                for m in ar.findall('m'):
                    t = m.get('t')
                    # Wir filtern nach echten Textmeldungen (Typ 'f' oder 'd')
                    if m.get('cat') in ['f', 'd']:
                        msg_text = m.get('c', '') # Hier steht der Grund-Code oder Text
                changes[s_id] = {"ct": ct, "msg": msg_text}

        fahrplan = []
        # Durch geplante Züge gehen
        for s in root_plan.findall('s'):
            s_id = s.get('id')
            ar = s.find('ar') # Arrival/Ankunft (für Zerbst meist Durchgang)
            dp = s.find('dp') # Departure/Abfahrt
            
            if dp is not None:
                plan_zeit = dp.get('pt')[-4:] # HHMM
                zeit = f"{plan_zeit[:2]}:{plan_zeit[2:]}"
                
                linie = dp.get('l', '???')
                # Zugtyp (RE, RB) + Linie
                zug = f"{dp.get('tl', '')}{linie}"
                
                # Ziel (Letzte Station in 'ppth')
                weg = dp.get('ppth', '').split('|')
                ziel = weg[-1] if weg else "Unbekannt"
                
                gleis = dp.get('pp', '-')
                
                # Echtzeit-Infos einbauen
                info = "pünktlich"
                if s_id in changes:
                    c = changes[s_id]
                    if c['ct']:
                        diff = (datetime.strptime(c['ct'][-4:], "%H%M") - 
                                datetime.strptime(plan_zeit, "%H%M")).seconds // 60
                        if diff > 0:
                            info = f"+{diff}"
                            if c['msg']: info += f" {c['msg']}" # Grund hinzufügen

                fahrplan.append({
                    "zeit": zeit,
                    "linie": zug,
                    "ziel": ziel[:18],
                    "gleis": gleis,
                    "info": info,
                    "update": update_zeit
                })

        # Sortieren nach Zeit
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:6] if fahrplan else [{"zeit": "Noch", "linie": "Keine", "ziel": "Züge", "gleis": "-", "info": update_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "IRIS", "ziel": str(e)[:15], "gleis": "-", "info": update_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
