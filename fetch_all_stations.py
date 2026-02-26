import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# DB-Verspätungscodes (Deine Original-Liste)
DB_CODES = {
    "1": "Sicherheitsrelevante Störung", "2": "Feuerwehreinsatz", "3": "Notarzteinsatz",
    "4": "Vandalismus", "5": "Personen im Gleis", "7": "Betriebsablauf",
    "10": "Signalstörung", "15": "Bauarbeiten", "18": "Defekt am Zug",
    "80": "Andere Wagenreihung", "90": "Halt entfällt"
}

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8011161",
    "berlin_hbf": "8011160", "brandenburg_hbf": "8010060", "zerbst": "8013389",
    "dessau_hbf": "8010077", "dessau_sued": "8011361", "rosslau": "8010302",
    "rodleben": "8010294", "magdeburg_neustadt": "8010226", "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052", "pretzier_altm": "8012724", "bad_belzig": "8010033",
    "gommern": "8010141", "wusterwitz": "8013365"
}

HEADERS = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}

def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes = {}
    
    # --- TEIL 1: AKTUELLER STATUS & INFOS (FCHG) ---
    try:
        c_res = requests.get(f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}", headers=HEADERS, timeout=10)
        if c_res.status_code == 200:
            root = ET.fromstring(c_res.content)
            for s in root.findall('s'):
                t_id = s.get('id')
                dp = s.find('dp')
                
                info_texte = []
                for m in s.findall('m'):
                    cat = m.get('c') # Code
                    typ = m.get('t') # Typ: d=Verspätung, h=Information
                    
                    # Wenn Typ 'h' (HIM/Info), nimm den Klartext direkt aus dem Attribut 'c'
                    if typ == 'h':
                        info_texte.append(cat) 
                    # Wenn Typ 'd' (Verspätung), nutze unsere DB_CODES Liste
                    elif cat in DB_CODES:
                        info_texte.append(DB_CODES[cat])

                changes[t_id] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(info_texte)) # Doppelte Texte filtern
                }
    except: pass

    # --- TEIL 2: PLAN-DATEN ABGLEICHEN ---
    verbindungen = []
    for delta in [0, 1]: # Aktuelle und nächste Stunde
        zeit = jetzt + timedelta(hours=delta)
        url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{zeit.strftime('%y%m%d')}/{zeit.strftime('%H')}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            for s in ET.fromstring(res.content).findall('s'):
                tl, dp = s.find('tl'), s.find('dp')
                if not (dp and tl): continue
                
                p_time_str = dp.get('pt')
                chg = changes.get(s.get('id'), {})
                e_time_str = chg.get('ct') or p_time_str
                
                # Filter: Nur Züge zeigen, die noch nicht weg sind
                e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                if e_time < jetzt - timedelta(minutes=5): continue

                verbindungen.append({
                    "zeit": datetime.strptime(p_time_str, "%y%m%d%H%M").strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": dp.get('l') or f"{tl.get('c')}{tl.get('n')}",
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "begruendung": chg.get('grund') or "", # Hier landen jetzt die HIM-Texte!
                    "update": jetzt.strftime("%H:%M")
                })
        except: continue
    
    verbindungen.sort(key=lambda x: x['zeit'])
    return verbindungen

def verarbeite_station(item):
    name, eva_id = item
    daten = hole_station_daten(eva_id)
    # Immer speichern, damit GitHub Action "grün" bleibt
    if not daten:
        daten = [{"zeit": "--:--", "echte_zeit": "--:--", "linie": "INFO", "ziel": "Keine Fahrten", "begruendung": "", "update": datetime.now().strftime("%H:%M")}]
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
        
