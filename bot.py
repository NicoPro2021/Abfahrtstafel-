import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime

# Übersetzung der wichtigsten DB-Codes
DB_CODES = {
    "2": "Polizeieinsatz", "3": "Feuerwehreinsatz", "5": "Ärztliche Versorgung",
    "8": "Oberleitungsschaden", "11": "Störung am Triebfahrzeug", "16": "Weichenstörung",
    "17": "Signalstörung", "31": "Bauarbeiten", "40": "Stellwerksstörung",
    "80": "Umleitung", "91": "Signalstörung", "96": "Bauarbeiten"
}

def hole_daten():
    u_zeit = datetime.now().strftime("%H:%M")
    datum = datetime.now().strftime("%y%m%d")
    stunde = datetime.now().strftime("%H")
    
    # Zerbst/Anhalt ID: 8006654
    url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/8006654/{datum}/{stunde}"
    url_fchg = "https://iris.noncd.db.de/iris-tts/timetable/fchg/8006654"
    
    try:
        # 1. Echtzeit-Änderungen holen
        r_f = requests.get(url_fchg, timeout=10)
        root_f = ET.fromstring(r_f.content)
        changes = {}
        for s in root_f.findall('s'):
            s_id = s.get('id')
            ar = s.find('ar')
            if ar is not None:
                ct = ar.get('ct') # Korrigierte Zeit
                msg = ""
                for m in ar.findall('m'):
                    if m.get('cat') == 'f': # Realzeit-Meldung
                        code = m.get('c')
                        msg = DB_CODES.get(code, f"Störung ({code})")
                changes[s_id] = {'ct': ct, 'msg': msg}

        # 2. Plan-Daten holen
        r_p = requests.get(url_plan, timeout=10)
        root_p = ET.fromstring(r_p.content)
        
        fahrplan = []
        for s in root_p.findall('s'):
            s_id = s.get('id')
            dp = s.find('dp')
            tl = s.find('tl')
            
            if dp is not None and tl is not None:
                # Filter: Nur Züge, die RE oder RB sind (gegen Kassel-RT4-Bug)
                zugtyp = tl.get('c', '') # RE, RB, etc.
                if zugtyp not in ['RE', 'RB']: continue
                
                linie = f"{zugtyp}{tl.get('n', '')}"
                p_zeit = dp.get('pt')[-4:]
                zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                ziel = dp.get('ppth', '').split('|')[-1][:18]
                gleis = dp.get('pp', '-')
                
                # Info-Logik
                info = "pünktlich"
                if s_id in changes:
                    c = changes[s_id]
                    if c['ct']:
                        diff = (datetime.strptime(c['ct'][-4:], "%H%M") - 
                                datetime.strptime(p_zeit, "%H%M")).seconds // 60
                        info = f"+{diff} {c['msg']}".strip() if diff > 0 else c['msg']
                
                if not info: info = "pünktlich"

                fahrplan.append({
                    "zeit": zeit_str,
                    "linie": linie,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info[:30],
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
