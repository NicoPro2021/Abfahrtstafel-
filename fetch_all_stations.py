import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# VOLLSTÄNDIGE CODES
DB_CODES = {
    "1": "Sicherheitsrelevante Störung", "2": "Feuerwehreinsatz am Gleis",
    "3": "Notarzteinsatz am Gleis", "4": "Vandalismusschaden", "5": "Personen im Gleis",
    "7": "Verzögerungen im Betriebsablauf", "8": "Anschlussabwartung",
    "9": "Warten auf Gegenverkehr", "10": "Ausfall der Leit- und Sicherungstechnik",
    "15": "Bauarbeiten", "18": "Defekt am Zug", "21": "Türstörung",
    "38": "Defekt an der Klimaanlage", "43": "Kurzfristiger Personalausfall",
    "46": "Verspätung eines vorausfahrenden Zuges", "80": "Andere Wagenreihung",
    "90": "Kein Halt an diesem Bahnhof", "92": "Technische Störung am Zug"
}

# JETZT SIND WIRKLICH ALLE DEINE STATIONEN HINTERLEGT!
STATIONS = {
    "Bad Belzig": "8010031",
    "Berlin Hbf": "8011160",
    "Biederitz": "8011195",
    "Bitterfeld": "8010050",
    "Brandenburg Hbf": "8010060",
    "Dessau Hbf": "8010077",
    "Dessau Süd": "8011403",
    "Gommern": "8011673",
    "Güterglück": "8011705",
    "Leipzig Hbf": "8010205",
    "Leipzig Hbf (tief)": "8011037",
    "Magdeburg Hbf": "8010224",
    "Magdeburg Herrenkrug": "8012301",
    "Magdeburg Neustadt": "8012302",
    "Pretzier (Altm)": "8012683",
    "Rodleben": "8012818",
    "Roßlau (Elbe)": "8010302",
    "Wittenberge": "8010386",
    "Wolfen": "8013444",
    "Wusterwitz": "8013467",
    "Zerbst/Anhalt": "8013389"
}

HEADERS = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}

def hole_daten_fuer_stunde(eva_id, datum, stunde, changes, tz):
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200: return []
        root = ET.fromstring(res.content)
        verbindungen = []
        for s in root.findall('s'):
            trip_id = s.get('id')
            tl, dp = s.find('tl'), s.find('dp')
            if dp is not None and tl is not None:
                p_time_str = dp.get('pt')
                chg = changes.get(trip_id, {})
                
                e_time_str = chg.get('ct') or p_time_str
                
                p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                if e_time < datetime.now(tz) - timedelta(minutes=10): continue
                
                diff = int((e_time - p_time).total_seconds() / 60)
                
                verbindungen.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": dp.get('l') or f"{tl.get('c')}{tl.get('n')}",
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": "FÄLLT AUS" if chg.get('cs') == "c" else (f"+{diff}" if diff > 0 else "pünktlich"),
                    "begruendung": chg.get('grund') or ""
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
                msgs = [DB_CODES.get(m.get('c'), f"Code {m.get('c')}") for m in s.findall('m') if m.get('c')]
                changes[s.get('id')] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(msgs))
                }
    except: pass
    
    datum_j = jetzt.strftime("%y%m%d")
    liste = hole_daten_fuer_stunde(eva_id, datum_j, jetzt.strftime("%H"), changes, tz)
    naechste = jetzt + timedelta(hours=1)
    liste += hole_daten_fuer_stunde(eva_id, naechste.strftime("%y%m%d"), naechste.strftime("%H"), changes, tz)
    
    liste.sort(key=lambda x: x['zeit'])
    for e in liste: e["update"] = jetzt.strftime("%H:%M")
    return liste

def verarbeite_station(item):
    name, eva_id = item
    daten = hole_station_daten(eva_id)
    
    # Hier machen wir den Dateinamen fit für GitHub (kleingeschrieben mit Unterstrichen):
    # Aus "Bad Belzig" wird "bad_belzig.json"
    # Aus "Zerbst/Anhalt" wird "zerbst_anhalt.json"
    dateiname = name.lower().replace(" ", "_").replace("/", "_")
    
    with open(f"{dateiname}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
        
