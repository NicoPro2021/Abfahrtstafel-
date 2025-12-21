import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta

# DB Störungscodes für Klartext
DB_CODES = {
    "2": "Polizeieinsatz", "3": "Feuerwehreinsatz", "5": "Notarzt am Gleis",
    "8": "Oberleitungsschaden", "11": "Störung am Zug", "16": "Weichenstörung",
    "17": "Signalstörung", "31": "Bauarbeiten", "40": "Stellwerksstörung",
    "80": "Umleitung", "82": "Kurzfristiger Fahrzeugaustausch", "91": "Signalstörung", 
    "96": "Bauarbeiten", "98": "Unwetter"
}

def hole_daten():
    # Zeitkorrektur für Deutschland (+1 Std zu UTC im Winter)
    jetzt_lokal = datetime.now() + timedelta(hours=1) 
    u_zeit = jetzt_lokal.strftime("%H:%M")
    
    eva = "8006654" # Zerbst/Anhalt
    fahrplan_liste = []
    
    try:
        # 1. Echtzeit-Daten (Verspätungen/Infos) für den gesamten Bahnhof laden
        r_f = requests.get(f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{eva}", timeout=15)
        changes = {}
        if r_f.status_code == 200:
            root_f = ET.fromstring(r_f.content)
            for s in root_f.findall('s'):
                s_id = s.get('id')
                # Prüfe Abfahrt (dp) oder Ankunft (ar) auf Änderungen
                node = s.find('dp') if s.find('dp') is not None else s.find('ar')
                if node is not None:
                    ct = node.get('ct') # Korrigierte Zeit
                    msg = ""
                    for m in node.findall('m'):
                        if m.get('cat') in ['f', 'd']:
                            msg = DB_CODES.get(m.get('c'), "Störung")
                    changes[s_id] = {'ct': ct, 'msg': msg}

        # 2. Pläne für die nächsten 3 Stunden laden
        for i in range(3):
            scan_zeit = jetzt_lokal + timedelta(hours=i)
            datum = scan_zeit.strftime("%y%m%d")
            stunde = scan_zeit.strftime("%H")
            
            url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva}/{datum}/{stunde}"
            r_p = requests.get(url_plan, timeout=15)
            if r_p.status_code != 200: continue
            
            root_p = ET.fromstring(r_p.content)
            for s in root_p.findall('s'):
                s_id = s.get('id')
                dp = s.find('dp') # Departure-Node
                tl = s.find('tl') # Train-Line-Node
                
                if dp is not None and tl is not None:
                    # Filter: Nur RE und RB (RE13, RB42)
                    typ = tl.get('c', '')
                    if typ not in ['RE', 'RB']: continue
                    
                    p_zeit = dp.get('pt')[-4:] # Geplante Zeit HHMM
                    zeit_str = f"{p_zeit[:2]}:{p_zeit[2:]}"
                    
                    # Vergangene Züge der aktuellen Stunde ignorieren
                    if i == 0 and zeit_str < u_zeit: continue

                    linie = f"{typ}{tl.get('n', '') or tl.get('l', '')}"
                    ziel = dp.get('ppth', '').split('|')[-1][:18]
                    gleis = dp.get('pp', '-')
                    
                    # Echtzeit-Status berechnen
                    info = "pünktlich"
                    if s_id in changes:
                        c = changes[s_id]
                        if c['ct']:
                            # Verspätung berechnen
                            p_min = int(p_zeit[:2]) * 60 + int(p_zeit[2:])
                            c_zeit = c['ct'][-4:]
                            c_min = int(c_zeit[:2]) * 60 + int(c_zeit[2:])
                            diff = c_min - p_min
                            if 0 < diff < 480: # bis 8 Std Verspätung logisch
                                info = f"+{diff} {c['msg']}".strip()
                            else:
                                info = c['msg'] if c['msg'] else "pünktlich"
                        elif c['msg']:
                            info = c['msg']

                    fahrplan_liste.append({
                        "zeit": zeit_str,
                        "linie": linie,
                        "ziel": ziel,
                        "gleis": gleis,
                        "info": info[:35],
                        "update": u_zeit
                    })

        # Sortieren nach Uhrzeit
        fahrplan_liste.sort(key=lambda x: x['zeit'])
        
        # Duplikate entfernen
        final_result = []
        for f in fahrplan_liste:
            if not any(r['zeit'] == f['zeit'] and r['linie'] == f['linie'] for r in final_result):
                final_result.append(f)

        return final_result[:10] # Gibt bis zu 10 Verbindungen zurück

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
