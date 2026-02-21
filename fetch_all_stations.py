import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# VOLLSTÄNDIGE STATIONSLISTE (Inklusive Leipzig Tief und Zerbst Korrektur)
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "leipzig_hbf_tief": "8011161",
    "berlin_hbf": "8011160",
    "brandenburg_hbf": "8010060",
    "zerbst": "8013389",
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

def hole_daten_fuer_stunde(eva_id, datum, stunde, changes, tz):
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200: return []
        
        root = ET.fromstring(res.content)
        verbindungen = []
        for s in root.findall('s'):
            trip_id = s.get('id')
            tl = s.find('tl')
            dp = s.find('dp')
            if dp is not None and tl is not None:
                p_time_str = dp.get('pt')
                p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                chg = changes.get(trip_id, {})
                e_time_str = chg.get('ct') or p_time_str
                e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                # Nur Züge anzeigen, die nicht älter als 10 Minuten sind
                if e_time < datetime.now(tz) - timedelta(minutes=10): continue

                diff = int((e_time - p_time).total_seconds() / 60)
                linie = dp.get('l') or f"{tl.get('c')}{tl.get('n')}"
                
                info_text = "pünktlich"
                if chg.get('cs') == "c": info_text = "FÄLLT AUS"
                elif diff > 0: info_text = f"+{diff}"

                verbindungen.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": linie,
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": info_text,
                    "begruendung": chg.get('grund') or ""
                })
        return verbindungen
    except: return []

def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    
    # 1. Echtzeit-Änderungen (fchg) laden
    changes = {}
    try:
        c_res = requests.get(f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}", headers=HEADERS, timeout=10)
        if c_res.status_code == 200:
            c_root = ET.fromstring(c_res.content)
            for s in c_root.findall('s'):
                t_id = s.get('id')
                dp = s.find('dp')
                # Begründungen (HIM-Messages) sammeln
                msgs = [m.get('c') for m in s.findall('m') if m.get('c') and m.get('t') in ['d','r','f']]
                changes[t_id] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(msgs))
                }
    except: pass

    # 2. Plan für AKTUELLE und NÄCHSTE Stunde laden (Stundenscheibe fixen)
    datum_jetzt = jetzt.strftime("%y%m%d")
    stunde_jetzt = jetzt.strftime("%H")
    
    naechste_zeit = jetzt + timedelta(hours=1)
    datum_naechste = naechste_zeit.strftime("%y%m%d")
    stunde_naechste = naechste_zeit.strftime("%H") # Einrückung korrigiert!

    liste = hole_daten_fuer_stunde(eva_id, datum_jetzt, stunde_jetzt, changes, tz)
    liste += hole_daten_fuer_stunde(eva_id, datum_naechste, stunde_naechste, changes, tz)
    
    # Sortieren und Zeitstempel für die Webseite
    liste.sort(key=lambda x: x['zeit'])
    for eintrag in liste: eintrag["update"] = jetzt.strftime("%H:%M")
    
    return liste

def verarbeite_station(item):
    dateiname, eva_id = item
    daten = hole_station_daten(eva_id)
    if daten:
        # Speichert die JSON-Datei im aktuellen Verzeichnis
        with open(f"{dateiname}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Update abgeschlossen: {dateiname}")

if __name__ == "__main__":
    # ThreadPool für maximale Geschwindigkeit auf dem GitHub Server
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
    
