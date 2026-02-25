import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# --- KONFIGURATION ---
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# DB-Verspätungscodes und Bahnhofsmeldungen
DB_CODES = {
    "1": "Sicherheitsrelevante Störung", "2": "Feuerwehreinsatz", 
    "3": "Notarzteinsatz", "4": "Vandalismus", "5": "Personen im Gleis", 
    "7": "Betriebsablauf", "8": "Anschlussabwartung", "9": "Warten auf Gegenverkehr", 
    "10": "Signalstörung", "15": "Bauarbeiten", "18": "Defekt am Zug", 
    "21": "Türstörung", "38": "Defekt Klimaanlage", "43": "Personalausfall", 
    "46": "Vorausfahrender Zug", "80": "Andere Wagenreihung", "90": "Halt entfällt", 
    "92": "Technische Störung", "101": "Aufzug außer Betrieb", "102": "Fahrtreppe außer Betrieb"
}

# Stationen mit verifizierten EVA-IDs
STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8011161",
    "berlin_hbf": "8011160", "brandenburg_hbf": "8010060", "zerbst": "8013389",
    "dessau_hbf": "8010077", "dessau_sued": "8011361", "rosslau": "8010302",
    "rodleben": "8010294", "magdeburg_neustadt": "8010226", "magdeburg_herrenkrug": "8010225",
    "biederitz": "8010052", "pretzier_altm": "8012724", "bad_belzig": "8010033",
    "gommern": "8010141", "wusterwitz": "8013365"
}

HEADERS = {
    'DB-Client-Id': CLIENT_ID,
    'DB-Api-Key': CLIENT_SECRET,
    'accept': 'application/xml'
}

def hole_global_info():
    """Erstellt eine zentrale Status-Datei für das Dashboard-Menü."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    try:
        w_res = requests.get("https://wttr.in/Magdeburg?format=%c+%t", timeout=5)
        wetter = w_res.text if w_res.status_code == 200 else "Wetter n.v."
    except:
        wetter = "Wetter n.v."

    info = {
        "title": "DB Reisebegleiter System",
        "wetter": wetter,
        "status": "Online",
        "last_update": jetzt.strftime("%d.%m. %H:%M"),
        "nachricht": "Live-Daten inkl. Bahnhofs-Infos (Aufzüge/Bauarbeiten)."
    }
    with open("global_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=4)

def hole_bahnhof_infos(eva_id):
    """Holt aktuelle Änderungen und Bahnhofsmeldungen (HIM)."""
    changes = {}
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for s in root.findall('s'):
                t_id = s.get('id')
                dp = s.find('dp')
                
                # Meldungen sammeln (Verspätungscodes + Freitexte)
                msgs = []
                for m in s.findall('m'):
                    code = m.get('c')
                    if code in DB_CODES:
                        msgs.append(DB_CODES[code])
                    elif m.get('t') == 'h': # HIM Meldungen (Bahnhofstexte)
                        msgs.append(m.get('c'))
                
                changes[t_id] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "grund": " | ".join(dict.fromkeys(msgs))
                }
    except:
        pass
    return changes

def hole_station_daten(eva_id):
    """Abfrage des aktuellen Fahrplans für zwei Stunden."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes = hole_bahnhof_infos(eva_id)
    verbindungen = []

    for h_offset in [0, 1]:
        ziel_zeit = jetzt + timedelta(hours=h_offset)
        datum = ziel_zeit.strftime("%y%m%d")
        stunde = ziel_zeit.strftime("%H")
        
        url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200: continue
            
            root = ET.fromstring(res.content)
            for s in root.findall('s'):
                tl = s.find('tl')
                dp = s.find('dp')
                if not (dp and tl): continue

                p_time_str = dp.get('pt')
                p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                chg = changes.get(s.get('id'), {})
                e_time_str = chg.get('ct') or p_time_str
                e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)

                # Filter: Züge die bereits mehr als 5 Min weg sind ausblenden
                if e_time < jetzt - timedelta(minutes=5): continue

                diff = int((e_time - p_time).total_seconds() / 60)
                
                verbindungen.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "echte_zeit": e_time.strftime("%H:%M"),
                    "linie": dp.get('l') or f"{tl.get('c')}{tl.get('n')}",
                    "ziel": dp.get('ppth').split('|')[-1][:20],
                    "gleis": chg.get('cp') or dp.get('pp') or "-",
                    "info": "FÄLLT AUS" if chg.get('cs') == "c" else (f"+{diff}" if diff > 0 else "pünktlich"),
                    "grund": chg.get('grund') or "",
                    "update": jetzt.strftime("%H:%M")
                })
        except:
            continue

    verbindungen.sort(key=lambda x: x['zeit'])
    return verbindungen

def verarbeite_station(item):
    """Zentrale Funktion für den Thread-Pool."""
    name, eva_id = item
    try:
        daten = hole_station_daten(eva_id)
        # Fallback: Immer eine Datei schreiben, um den Status auf GitHub zu aktualisieren
        if not daten:
            daten = [{"zeit": "--:--", "linie": "INFO", "ziel": "Keine Fahrten", "update": datetime.now().strftime("%H:%M")}]
        
        with open(f"{name}.json", 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"✅ {name.upper()} aktualisiert.")
    except Exception as e:
        print(f"❌ Fehler bei {name}: {e}")

if __name__ == "__main__":
    print("Starte Update-Prozess...")
    hole_global_info()
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())
    print("Alle Stationen verarbeitet.")
        
