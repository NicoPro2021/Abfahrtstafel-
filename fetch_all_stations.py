import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

# Vollständige Liste deiner Stationen mit Namen und IDs
STATIONS = {
    "magdeburg_hbf": "8010224",
    "leipzig_hbf": "Leipzig Hbf",
    "berlin_hbf": "Berlin Hbf",
    "brandenburg_hbf": "Brandenburg Hbf",
    "opernhaus_magdeburg": "692138",
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
} # <--- Hier war der Fehler: Die Klammer ist jetzt zu!

def hole_daten(identifier, dateiname):
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    headers = {'User-Agent': 'Mozilla/5.0 (BahnMonitorBot/6.0)'}

    try:
        final_id = identifier
        if not identifier.isdigit():
            s_res = requests.get(f"https://v6.db.transport.rest/locations?query={identifier}&results=1", headers=headers, timeout=10)
            s_data = s_res.json()
            final_id = s_data[0]['id'] if s_data else None

        if not final_id: return None

        res_api = requests.get(f"https://v6.db.transport.rest/stops/{final_id}/departures?duration=180&remarks=true", headers=headers, timeout=15)
        if res_api.status_code != 200: return None

        r = res_api.json()
        departures = r.get('departures', [])

        if not departures:
            return [{"update": u_zeit, "info": "Keine Fahrten"}]

        res_list = []
        for d in departures:
            try:
                line = d.get('line', {})
                planned = datetime.fromisoformat((d.get('plannedWhen') or d.get('when')).replace('Z', '+00:00'))
                actual = datetime.fromisoformat((d.get('when') or d.get('plannedWhen')).replace('Z', '+00:00'))
                diff = int((actual - planned).total_seconds() / 60)

                remarks = d.get('remarks', [])
                grund_liste = []
                
                load = d.get('load')
                if load:
                    icons = ["👤", "👤👤", "👤👤👤", "❗👤"]
                    grund_liste.append(f"Auslastung: {icons[load-1] if load <= 4 else ''}")

                for rem in remarks:
                    text = rem.get('text', '').strip()
                    if text and "http" not in text:
                        t = text.replace("Fahrradmitnahme möglich", "🚲")
                        if t not in grund_liste: grund_liste.append(t)
                
                grund_final = " | ".join(grund_liste)

                res_list.append({
                    "zeit": planned.strftime("%H:%M"), 
                    "echte_zeit": actual.strftime("%H:%M"), 
                    "linie": line.get('name', '').replace(" ", ""), 
                    "ziel": d.get('direction', '')[:18], 
                    "gleis": str(d.get('platform') or "-"), 
                    "info": "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else ""), 
                    "grund": grund_final,
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

   
