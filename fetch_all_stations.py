import requests
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor # Neu für Parallelisierung

STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "Leipzig Hbf",
    "berlin_hbf": "Berlin Hbf",
    "brandenburg_hbf": "Brandenburg Hbf",
    "opernhaus_magdeburg": "Magdeburg Opernhaus",
    "zerbst": "Zerbst/Anhalt",
    "dessau_hbf": "8010077",
    "dessau_sued": "Dessau Süd",
    "rosslau": "8010297",
    "rodleben": "rodleben",
    "magdeburg_neustadt": "8010226",
    "magdeburg_herrenkrug": "Magdeburg Herrenkrug",
    "biederitz": "Biederitz",
    "pretzier_altm": "Pretzier Altm",
    "bad_belzig": "Bad Belzig",
    "gommern": "Gommern",
    "wusterwitz": "Wusterwitz"
}

def hole_daten(identifier):
    # Da Threads keine gemeinsame Session einfach teilen sollten ohne Lock, 
    # erstellen wir hier eine einfache Anfrage oder nutzen eine globale Session.
    tz = ZoneInfo("Europe/Berlin")
    u_zeit = datetime.now(tz).strftime("%H:%M")
    headers = {'User-Agent': 'BahnMonitorBot/6.0'}

    try:
        final_id = identifier
        if not identifier.isdigit():
            s_res = requests.get(f"https://v6.db.transport.rest/locations?query={identifier}&results=1", headers=headers, timeout=10)
            s_data = s_res.json()
            if not s_data: return None
            final_id = s_data[0]['id']

        res_api = requests.get(f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&remarks=true", headers=headers, timeout=15)
        if res_api.status_code != 200: return None

        r = res_api.json()
        departures = r.get('departures', [])
        if not departures: return [{"update": u_zeit, "info": "Keine Fahrten"}]

        res_list = []
        for d in departures:
            try:
                line = d.get('line', {})
                p_time = datetime.fromisoformat(d['plannedWhen']).astimezone(tz)
                actual_val = d.get('when') or d.get('plannedWhen')
                a_time = datetime.fromisoformat(actual_val).astimezone(tz)
                diff = int((a_time - p_time).total_seconds() / 60)
                
                remarks = d.get('remarks', [])
                grund_liste = []
                load = d.get('load')
                if load and 1 <= load <= 4:
                    icons = ["👤", "👤👤", "👤👤👤", "❗👤"]
                    grund_liste.append(f"Auslastung: {icons[load-1]}")

                for rem in remarks:
                    text = rem.get('text', '').strip()
                    if text and "http" not in text and "Fahrrad" not in text:
                        if text not in grund_liste: grund_liste.append(text)
                
                res_list.append({
                    "zeit": p_time.strftime("%H:%M"), 
                    "echte_zeit": a_time.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:20], 
                    "gleis": str(d.get('platform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else ""), 
                    "grund": " | ".join(grund_liste),
                    "update": u_zeit
                })
            except: continue
        return res_list
    except: return None

def verarbeite_station(item):
    """ Hilfsfunktion für den ThreadPool """
    dateiname, identifier = item
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Starte Abfrage: {dateiname}...")
    daten = hole_daten(identifier)
    
    if daten is not None:
        with open(os.path.join(base_path, f"{dateiname}.json"), 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=4)
        print(f"Fertig: {dateiname}")

if __name__ == "__main__":
    start_time = time.time()
    
    # max_workers=10 bedeutet, dass bis zu 10 Stationen gleichzeitig abgefragt werden.
    # Man sollte es nicht zu hoch setzen, damit die API einen nicht sperrt.
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(verarbeite_station, STATIONS.items())

    end_time = time.time()
    print(f"\nAlle Stationen in {round(end_time - start_time, 2)} Sekunden aktualisiert.")
    
