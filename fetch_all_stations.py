import requests
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
import json

# DEINE NEUEN ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# WICHTIG: Die offizielle API braucht zwingend die numerische EVA-ID
STATIONS = {
    "magdeburg_hbf": "8010224",
    "dessau_hbf": "8010077",
    "rosslau": "8010297",
    "magdeburg_neustadt": "8010226",
    # Füge hier die weiteren numerischen IDs hinzu
}

def hole_daten_offiziell(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    u_zeit = jetzt.strftime("%H:%M")
    
    # Format für die offizielle API: YYMMDD/HH
    datum = jetzt.strftime("%y%m%d")
    stunde = jetzt.strftime("%H")
    
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    
    headers = {
        'DB-Client-Id': CLIENT_ID,
        'DB-Api-Key': CLIENT_SECRET,
        'accept': 'application/xml'
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"Fehler {res.status_code} bei ID {eva_id}")
            return None

        # XML parsen
        root = ET.fromstring(res.content)
        res_list = []

        for s in root.findall('s'):
            # Abfahrts-Informationen (dp = departure)
            dp = s.find('dp')
            tl = s.find('tl') # Train-Logik
            
            if dp is not None and tl is not None:
                # Geplante Zeit (Format: YYMMDDHHMM)
                p_time_str = dp.get('pt')
                p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
                
                res_list.append({
                    "zeit": p_time.strftime("%H:%M"),
                    "linie": (tl.get('c') or "") + (tl.get('n') or ""), # z.B. RE13
                    "ziel": dp.get('ppth').split('|')[-1], # Letztes Ziel in der Route
                    "gleis": dp.get('pp') or "-",
                    "info": "", # Verspätungen müssten über die /fchg-Schnittstelle geladen werden
                    "update": u_zeit
                })
        
        return res_list if res_list else [{"update": u_zeit, "info": "Keine Fahrten"}]
    except Exception as e:
        print(f"Fehler: {e}")
        return None

def verarbeite_station(item):
    dateiname, identifier = item
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check, ob wir eine Nummer haben (die offizielle API kann keine Namen suchen)
    if not identifier.isdigit():
        print(f"Überspringe {dateiname}: Benötige numerische EVA-ID!")
        return

    daten = hole_daten_offiziell(identifier)
    
    if daten is not None:
        file_path = os.path.join(base_path, f"{dateiname}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Erfolgreich aktualisiert: {dateiname}")

if __name__ == "__main__":
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor: # Weniger Worker, um DB-Sperren zu vermeiden
        executor.map(verarbeite_station, STATIONS.items())
    
    print(f"\nUpdate beendet in {round(time.time() - start_time, 2)} Sek.")
    
