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
    # Zeitkorrektur für Deutschland (Winterzeit)
    jetzt_lokal = datetime.now() + timedelta(hours=1) 
    u_zeit = jetzt_lokal.strftime("%H:%M")
    
    # Suche für die aktuelle und die nächsten zwei Stunden
    stunden_liste = [jetzt_lokal, jetzt_lokal + timedelta(hours=1), jetzt_lokal + timedelta(hours=2)]
    station_id = "8006654" # Zerbst/Anhalt
    
    try:
        # 1. Echtzeit-Daten (Meldungen und Zeitkorrekturen)
        r_f = requests.get(f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{station_id}", timeout=15)
        changes = {}
        if r_f.status_code == 200:
            root_f = ET.fromstring(r_f.content)
            for s in root_f.findall('s'):
                s_id = s.get('id')
                ar = s.find('ar')
                dp = s.find('dp')
                node = dp if dp is not None else ar
                if node is not None:
                    ct = node.get('ct')
                    msg = ""
                    for m in node.findall('m'):
                        if m.get('cat') in ['f', 'd']:
                            msg = DB_CODES.get(m.get('c'), "Störung")
                    changes[s_id] = {'ct': ct, 'msg': msg}

        # 2. Pläne laden
        fahrplan = []
        for zeit_obj in stunden_liste:
            datum = zeit_obj.strftime("%y%m%d")
            stunde = zeit_obj.strftime("%H")
            url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{station_id}/{datum}/{stunde}"
            
            r_p = requests.get(url_plan, timeout=15)
            if r_p.status_code != 200: continue
            
            root_p = ET.fromstring(r_p.content)
            for s in root_p.findall('s'):
                s_id = s.get('id')
                dp = s.find('dp') # Departure
                tl = s.find('tl') # Train Info
                
                if dp is not None:
                    # Wir nehmen alles, was eine Liniennummer hat (RE13, RB42)
                    zug_name = tl.get('c', '') + (tl.get('n', '') or tl.get('l', ''))
                    if not zug_name or "RT" in zug_name: continue
                    
                    p_zeit = dp.get('pt')[-4:] # HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Zeit-Filter: Nur zukünftige Züge
                    if zeit_obj.strftime("%H") == jetzt_lokal.strftime("%H") and zeit_str < u_zeit:
                        continue

                    # Ziel aus Pfad extrahieren
                    pfad = dp.get('ppth', '').split('|')
                    ziel = pfad[-1] if pfad else "Ziel unbekannt"
                    gleis = dp.get('pp', '-')
                    
                    info = "pünktlich"
                    if s_id in changes:
                        c = changes[s_id]
                        if c['ct']:
                            info = f"Verspätung {c['msg']}".strip() if c['msg'] else "Verspätung"
                        elif c['msg']:
                            info = c['msg']

                    fahrplan.append({
                        "zeit": zeit_str,
                        "linie": zug_name,
                        "ziel": ziel[:18],
                        "gleis": gleis,
                        "info": info[:35],
                        "update": u_zeit
                    })

        fahrplan.sort(key=lambda x: x['zeit'])
        # Duplikate entfernen (falls Züge stundenübergreifend gelistet sind)
        gesehen = set()
        einzigartig = []
        for f in fahrplan:
            key = f['zeit'] + f['linie']
            if key not in gesehen:
                einzigartig.append(f)
                gesehen.add(key)

        return einzigartig[:6] if einzigartig else [{"zeit": "INFO", "linie": "DB", "ziel": "Suche RE13...", "gleis": "-", "info": u_zeit}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
