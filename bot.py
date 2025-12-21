import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

# Wichtige DB-Codes für Zerbst
DB_CODES = {
    "2": "Polizeieinsatz", "3": "Feuerwehreinsatz", "5": "Ärztliche Versorgung",
    "8": "Oberleitungsschaden", "11": "Störung am Zug", "16": "Weichenstörung",
    "17": "Signalstörung", "31": "Bauarbeiten", "40": "Stellwerksstörung",
    "80": "Umleitung", "91": "Signalstörung", "96": "Bauarbeiten"
}

def hole_daten():
    jetzt = datetime.now()
    u_zeit = jetzt.strftime("%H:%M")
    
    # Wir laden die aktuelle Stunde UND die nächste Stunde
    stunden = [jetzt, jetzt + timedelta(hours=1)]
    station_id = "8006654" # Zerbst/Anhalt
    
    try:
        # 1. Echtzeit-Änderungen (für alle Züge gleich)
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
                    if m.get('cat') == 'f':
                        msg = DB_CODES.get(m.get('c'), f"Störung")
                changes[s_id] = {'ct': ct, 'msg': msg}

        # 2. Pläne für beide Stunden laden
        fahrplan = []
        for zeit_obj in stunden:
            datum = zeit_obj.strftime("%y%m%d")
            stunde = zeit_obj.strftime("%H")
            url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{station_id}/{datum}/{stunde}"
            
            r_p = requests.get(url_plan, timeout=10)
            root_p = ET.fromstring(r_p.content)
            
            for s in root_p.findall('s'):
                s_id = s.get('id')
                dp = s.find('dp')
                tl = s.find('tl')
                
                if dp is not None and tl is not None:
                    zugtyp = tl.get('c', '')
                    if zugtyp not in ['RE', 'RB']: continue
                    
                    p_zeit = dp.get('pt')[-4:]
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Nur Züge anzeigen, die noch nicht abgefahren sind
                    if zeit_obj == stunden[0] and zeit_str < jetzt.strftime("%H:%M"):
                        continue

                    ziel = dp.get('ppth', '').split('|')[-1][:18]
                    gleis = dp.get('pp', '-')
                    
                    info = "pünktlich"
                    if s_id in changes:
                        c = changes[s_id]
                        if c['ct']:
                            # Verspätung in Minuten berechnen
                            diff = (datetime.strptime(c['ct'][-4:], "%H%M") - 
                                    datetime.strptime(p_zeit, "%H%M")).seconds // 60
                            if diff > 1400: diff = 0 # Tageswechsel-Bug abfangen
                            info = f"+{diff} {c['msg']}".strip() if diff > 0 else c['msg']
                    
                    if not info: info = "pünktlich"

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
        return [{"zeit": "Error", "linie": "IRIS", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
