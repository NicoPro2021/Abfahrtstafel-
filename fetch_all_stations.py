import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# VOLLSTÄNDIGE STATIONSLISTE
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "berlin_hbf": "8011160",
    "brandenburg_hbf": "8010060",
    "zerbst": "8010392",
    "dessau_hbf": "8010077",
    "dessau_sued": "8010076",
    "rosslau": "8010297",
    "rodleben": "8010294",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052",
    "pretzier_altm": "8012724",
    "bad_belzig": "8010033",
    "gommern": "8010141",
    "wusterwitz": "8010388"
}

HEADERS = {
    'DB-Client-Id': CLIENT_ID,
    'DB-Api-Key': CLIENT_SECRET,
    'accept': 'application/xml'
}

def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    u_zeit = jetzt.strftime("%H:%M")
    
    datum = jetzt.strftime("%y%m%d")
    stunde = jetzt.strftime("%H")
    
    plan_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    change_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}"

    try:
        # 1. ÄNDERUNGEN UND BEGRÜNDUNGEN LADEN (fchg)
        changes = {}
        c_res = requests.get(change_url, headers=HEADERS, timeout=12)
        if c_res.status_code == 200:
            c_root = ET.fromstring(c_res.content)
            for s in c_root.findall('s'):
                t_id = s.get('id')
                dp = s.find('dp')
                
                # Begründungen sammeln (HIM-Meldungen)
                messages = []
                for m in s.findall('m'):
                    # Wir suchen nach Verspätungsgründen (t='d') oder Störungen (t='r')
                    grund = m.get('c')
                    if grund and m.get('t') in ['d', 'r', 'f']:
                        # Manche Gründe sind nur Codes, oft liefert die API aber Text
                        messages.append(grund)
                
                changes[t_id] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(messages)) # Dubletten entfernen
                }

        # 2. PLAN-DATEN LADEN
        p_res = requests.get(plan_url, headers=HEADERS, timeout=12)
        if p_res.status_code != 200: return None
        
        p_root = ET.fromstring(p_res.content)
        res_list = []

        for s in p_root.findall('s'):
            trip_id = s.get('id')
            tl = s.find('tl')
            dp = s.find('dp')
            
            if dp is not None and tl is not None:
                p_time_str = dp.get('pt')
                p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                # Abgleich mit Echtzeit-Daten
                chg = changes.get(trip_id, {})
                e_time_str = chg.get('ct') or p_time_str
                e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                diff = int((e_time - p_time).total_seconds() / 60)
                
                # Linie (RE13 etc.)
                linie = dp.get('l') or f"{tl.get('c')}{tl.get('n')}"
                
                # Status-Text (Verspätung oder Ausfall)
                info_text = "pünktlich"
                if chg.get('cs') == "c":
                    info_text = "FÄLLT AUS"
                elif diff > 0:
                    info_text = f"+{diff}"

                res_list.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": linie,
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": info_text,
                    "begruendung": chg.get('messages') or "", # Die neue Spalte für den Grund
                    "update": u_zeit
                })
        
        res_list.sort(key=lambda x: x['zeit'])
        return res_list

    except Exception as e:
        print(f"Fehler bei Station {eva_id}: {e}")
        return None

def verarbeite_station(item):
    dateiname, eva_id = item
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Abfrage läuft: {dateiname} (ID: {eva_id})")
    daten = hole_station_daten(eva_id)
    
    if daten is not None:
        file_path = os.path.join(base_path, f"{dateiname}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Datei gespeichert: {dateiname}.json")

if __name__ == "__main__":
    print("Starte Bahn-Monitor Update...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
        
    print(f"\nUpdate abgeschlossen! Dauer: {round(time.time() - start_time, 2)} Sekunden.")
