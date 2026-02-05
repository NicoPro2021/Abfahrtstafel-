import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "Leipzig Hbf", "zerbst": "Zerbst/Anhalt",
    "dessau_hbf": "8010077", "dessau_sued": "Dessau Süd", "rosslau": "8010297",
    "rodleben": "rodleben", "magdeburg_neustadt": "8010226", "magdeburg_herrenkrug": "Magdeburg Herrenkrug",
    "biederitz": "Biederitz", "pretzier_altm": "Pretzier Altm", "bad_belzig": "Bad Belzig",
    "gommern": "Gommern", "wusterwitz": "Wusterwitz"
}

def hole_daten(identifier, dateiname):
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'Mozilla/5.0 (BahnMonitorBot/6.0)'}
    try:
        final_id = identifier
        if not identifier.isdigit():
            s_res = requests.get(f"https://v6.db.transport.rest/locations?query={identifier}&results=1", headers=headers, timeout=10)
            final_id = s_res.json()[0]['id'] if s_res.json() else None
        if not final_id: return None

        # remarks=true ist gesetzt
        res_api = requests.get(f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&remarks=true", headers=headers, timeout=15)
        r = res_api.json()
        departures = r.get('departures', [])
        
        res_list = []
        for d in departures:
            try:
                line = d.get('line', {})
                planned = datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))
                actual = datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00'))
                diff = int((actual - planned).total_seconds() / 60)

                # --- ALLE FILTER ENTFERNT ---
                remarks = d.get('remarks', [])
                grund_liste = []
                
                # Jede einzelne Bemerkung wird hinzugefügt
                for rem in remarks:
                    text = rem.get('text', '').strip()
                    if text:
                        grund_liste.append(text)
                
                # Auch die Auslastung direkt dazu
                load = d.get('load')
                if load:
                    grund_liste.append(f"Load: {load}")

                res_list.append({
                    "zeit": planned.strftime("%H:%M"),
                    "echte_zeit": actual.strftime("%H:%M"),
                    "linie": line.get('name', '').replace(" ", ""),
                    "ziel": d.get('direction', '')[:18],
                    "gleis": str(d.get('platform') or "-"),
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else ""),
                    "grund": " | ".join(grund_liste), # Alles wird hier reingeschrieben
                    "update": u_zeit
                })
            except: continue
        return res_list
    except: return None

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    for dateiname, identifier in STATIONS.items():
        daten = hole_daten(identifier, dateiname)
        if daten is not None:
            with open(os.path.join(base_path, f"{dateiname}.json"), 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
        time.sleep(2)
        
