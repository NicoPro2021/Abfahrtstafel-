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

# DB-Verspätungscodes
DB_CODES = {
    "1": "Sicherheitsrelevante Störung", "2": "Feuerwehreinsatz", "3": "Notarzteinsatz",
    "4": "Vandalismus", "5": "Personen im Gleis", "7": "Betriebsablauf",
    "8": "Anschlussabwartung", "9": "Warten auf Gegenverkehr", "10": "Signalstörung",
    "15": "Bauarbeiten", "18": "Defekt am Zug", "21": "Türstörung",
    "38": "Defekt Klimaanlage", "43": "Personalausfall", "46": "Vorausfahrender Zug",
    "80": "Andere Wagenreihung", "90": "Halt entfällt", "92": "Technische Störung"
}

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "berlin_hbf": "8011160",
    "dessau_hbf": "8010077", "rosslau": "8010302", "zerbst": "8013389",
    "magdeburg_neustadt": "8010226", "bad_belzig": "8010033"
}

HEADERS = {
    'DB-Client-Id': CLIENT_ID,
    'DB-Api-Key': CLIENT_SECRET,
    'accept': 'application/xml'
}

def hole_global_info():
    """Erstellt die zentrale Informationsquelle für das Dashboard."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    try:
        # Einfaches Wetter-Abfrage (Beispiel für Magdeburg)
        w_res = requests.get("https://wttr.in/Magdeburg?format=%c+%t", timeout=5)
        wetter = w_res.text if w_res.status_code == 200 else "Wetter n.v."
    except:
        wetter = "Wetter n.v."

    info = {
        "title": "Zentrale Informationsquelle",
        "wetter": wetter,
        "status": "System Online",
        "last_update": jetzt.strftime("%d.%m. %H:%M"),
        "nachricht": "Daten werden direkt über die DB-API v1 bezogen."
    }
    with open("global_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=4)

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
                if e_time < datetime.now(tz) - timedelta(minutes=10): continue
                diff = int((e_time - p_time).total_seconds() / 60)
                
                verbindungen.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "linie": dp.get('l') or f"{tl.get('c')}{tl.get('n')}",
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": "FÄLLT AUS" if chg.get('cs') == "c" else (f"+{diff}" if diff > 0 else "pünktlich"),
                    "grund": chg.get('grund') or ""
                })
        return verbindungen
    except: return []

def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes = {}
    try:
        c_res = requests.get(f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}", headers=HEADERS, timeout=10)
        if c_res.status_code == 200:
            for s in ET.fromstring(c_res.content).findall('s'):
                dp = s.find('dp')
                begruendungen = [DB_CODES[m.get('c')] for m in s.findall('m') if m.get('c') in DB_CODES]
                changes[s.get('id')] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(begruendungen))
                }
    except: pass
    
    datum_jetzt = jetzt.strftime("%y%m%d")
    liste = hole_daten_fuer_stunde(eva_id, datum_jetzt, jetzt.strftime("%H"), changes, tz)
    # Nächste Stunde ebenfalls laden für lückenlosen Übergang
    naechste = jetzt + timedelta(hours=1)
    liste += hole_daten_fuer_stunde(eva_id, naechste.strftime("%y%m%d"), naechste.strftime("%H"), changes, tz)
    
    liste.sort(key=lambda x: x['zeit'])
    for e in liste: e["update"] = jetzt.strftime("%H:%M")
    return liste

def verarbeite_station(item):
    name, eva_id = item
    daten = hole_station_daten(eva_id)
    if daten:
        with open(f"{name}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    hole_global_info()
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
