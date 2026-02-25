import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# --- ZUGANGSDATEN ---
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# --- KONFIGURATION ---
# Wichtig: Diese Namen müssen exakt so heißen wie deine .json Dateien im Repo!
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "8010205",
    "berlin_hbf": "8011160",
    "dessau_hbf": "8010077",
    "dessau_sued": "8011361",
    "rosslau": "8010302",
    "zerbst": "8013389",
    "bad_belzig": "8010033",
    "biederitz": "8010052",
    "rodleben": "8010294",
    "gommern": "8010141",
    "wusterwitz": "8013365",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "8010225",
    "pretzier_altm": "8012724",
    "brandenburg_hbf": "8010060"
}

# DB-Codes für Verspätungen und Bahnhofs-Infos (Aufzüge etc.)
DB_CODES = {
    "1": "Sicherheitsrelevante Störung", "2": "Feuerwehreinsatz", "3": "Notarzteinsatz",
    "4": "Vandalismus", "5": "Personen im Gleis", "7": "Betriebsablauf",
    "10": "Signalstörung", "15": "Bauarbeiten", "18": "Defekt am Zug",
    "80": "Andere Wagenreihung", "90": "Halt entfällt",
    "101": "Aufzug außer Betrieb", "102": "Fahrtreppe außer Betrieb",
    "103": "Aufzug wieder in Betrieb"
}

HEADERS = {
    'DB-Client-Id': CLIENT_ID,
    'DB-Api-Key': CLIENT_SECRET,
    'accept': 'application/xml'
}

def hole_global_info():
    """Erstellt die zentrale Info-Quelle für das Dashboard."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    try:
        # Wetter für die Region
        w_res = requests.get("https://wttr.in/Magdeburg?format=%c+%t", timeout=5)
        wetter = w_res.text if w_res.status_code == 200 else "☀️ --°C"
    except: wetter = "☀️ --°C"

    info = {
        "title": "Zentrale Informationsquelle",
        "wetter": wetter,
        "status": "System Online",
        "last_update": jetzt.strftime("%d.%m. %H:%M"),
        "nachricht": "Live-Daten inkl. Bahnhofs-Infos (HIM/Aufzüge)."
    }
    with open("global_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=4)

def hole_bahnhof_meldungen(eva_id):
    """Sammelt aktuelle Störungsmeldungen und Bahnhofs-Infos (HIM)."""
    changes = {}
    try:
        url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for s in root.findall('s'):
                t_id = s.get('id')
                dp = s.find('dp')
                msgs = []
                for m in s.findall('m'):
                    c = m.get('c')
                    # Nutze Übersetzung oder Freitext bei HIM-Meldungen (Typ 'h')
                    text = DB_CODES.get(c) or (m.get('c') if m.get('t') == 'h' else None)
                    if text: msgs.append(text)
                
                changes[t_id] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(msgs))
                }
    except: pass
    return changes

def hole_station_daten(eva_id):
    """Lädt den Fahrplan und verknüpft ihn mit aktuellen Infos."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes = hole_bahnhof_meldungen(eva_id)
    ergebnisse = []

    # Abfrage für aktuelle und nächste Stunde
    for delta in [0, 1]:
        zeit = jetzt + timedelta(hours=delta)
        url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{zeit.strftime('%y%m%d')}/{zeit.strftime('%H')}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            root = ET.fromstring(res.content)
            for s in root.findall('s'):
                tl, dp = s.find('tl'), s.find('dp')
                if not (dp and tl): continue

                p_time = datetime.strptime(dp.get('pt'), "%y%m%d%H%M").replace(tzinfo=tz)
                chg = changes.get(s.get('id'), {})
                e_time = datetime.strptime(chg.get('ct') or dp.get('pt'), "%y%m%d%H%M").replace(tzinfo=tz)

                # Nur Züge zeigen, die noch nicht lange weg sind
                if e_time < jetzt - timedelta(minutes=5): continue

                diff = int((e_time - p_time).total_seconds() / 60)
                ergebnisse.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": dp.get('l') or f"{tl.get('c')}{tl.get('n')}",
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": "FÄLLT AUS" if chg.get('cs') == "c" else (f"+{diff}" if diff > 0 else "pünktlich"),
                    "grund": chg.get('grund') or "",
                    "update": jetzt.strftime("%H:%M")
                })
        except: continue
    
    ergebnisse.sort(key=lambda x: x['zeit'])
    return ergebnisse

def verarbeite_station(item):
    name, eva_id = item
    try:
        daten = hole_station_daten(eva_id)
        # Wenn keine Züge gefunden wurden, schreibe trotzdem eine Datei für GitHub (Status "now")
        if not daten:
            daten = [{"zeit": "--:--", "echte_zeit": "--:--", "linie": "INFO", "ziel": "Keine Fahrten", "info": "Kein Betrieb", "update": datetime.now().strftime("%H:%M")}]
        
        with open(f"{name}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Update ok: {name}")
    except Exception as e:
        print(f"Fehler bei {name}: {e}")

if __name__ == "__main__":
    hole_global_info()
    # Mit 5 Threads parallel abfragen für Speed
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
                
