import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

# Deutsche Bahn Störungscodes
DB_CODES = {
    "2": "Polizeieinsatz", "3": "Feuerwehreinsatz", "5": "Ärztliche Versorgung",
    "8": "Oberleitungsschaden", "11": "Störung am Zug", "16": "Weichenstörung",
    "17": "Signalstörung", "31": "Bauarbeiten", "40": "Stellwerksstörung",
    "80": "Umleitung", "91": "Signalstörung", "96": "Bauarbeiten"
}

def hole_daten():
    # Zeitkorrektur für Deutschland (+1 Std im Winter)
    jetzt_utc = datetime.utcnow()
    jetzt_lokal = jetzt_utc + timedelta(hours=1) 
    u_zeit = jetzt_lokal.strftime("%H:%M")
    
    # Wir laden die aktuelle und die nächste Stunde
    stunden = [jetzt_lokal, jetzt_lokal + timedelta(hours=1)]
    station_id = "8006654" # Zerbst/Anhalt
    
    try:
        # 1. Echtzeit-Daten (fchg) laden
        r_f = requests.get(f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{station_id}", timeout=10)
        root_f = ET.fromstring(r_f.content)
        changes = {}
        for s in root_f.findall('s'):
            s_id = s.get('id')
            ar = s.find('ar')
            if ar is not None:
                ct = ar.get('ct') # Korrigierte Zeit
                msg = ""
                for m in ar.findall('m'):
                    if m.get('cat') in ['f', 'd']:
                        msg = DB_CODES.get(m.get('c'), "Störung")
                changes[s_id] = {'ct': ct, 'msg': msg}

        # 2. Pläne (plan) laden
        fahrplan = []
        for zeit_obj in stunden:
            datum = zeit_obj.strftime("%y%m%d")
            stunde = zeit_obj.strftime("%H")
            url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{station_id}/{datum}/{stunde}"
            
            r_p = requests.get(url_plan, timeout=10)
            root_p = ET.fromstring(r_p.content)
            
            for s in root_p.findall('s'):
                s_id = s.get('id')
                dp = s.find('dp') # Departure
                tl = s.find('tl') # Train Line
                
                if dp is not None and tl is not None:
                    zugtyp = tl.get('c', '')
                    # Wir lassen RE und RB zu (RE13 / RB42)
                    if zugtyp not in ['RE', 'RB']: continue
                    
                    p_zeit = dp.get('pt')[-4:] # Geplante Zeit HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Nur Züge anzeigen, die noch kommen
                    if zeit_obj.strftime("%H") == jetzt_lokal.strftime("%H") and zeit_str < u_zeit:
                        continue

                    ziel = dp.get('ppth', '').split('|')[-1][:18]
                    gleis = dp.get('pp', '-')
                    
                    info = "pünktlich"
                    if s_id in changes:
                        c = changes[s_id]
                        if c['ct']:
                            # Verspätung berechnen
                            p_min = int(p_zeit[:2]) * 60 + int(p_zeit[2:])
                            c_zeit = c['ct'][-4:]
                            c_min = int(c_zeit[:2]) * 60 + int(c_zeit[2:])
                            diff = c_min - p_min
                            if 0 < diff < 500: # Plausible Verspätung
                                info = f"+{diff} {c['msg']}".strip()
                            elif c['msg']:
                                info = c['msg']

                    fahrplan.append({
                        "zeit": zeit_str,
                        "linie": f"{zugtyp}{tl.get('n', '')}",
                        "ziel": ziel,
                        "gleis": gleis,
                        "info": info[:35],
                        "update": u_zeit
                    })

        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:6] if fahrplan else [{"zeit": "INFO", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": u_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "IRIS", "ziel": "Verbindung..", "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
