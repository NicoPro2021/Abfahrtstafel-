import requests, json
from datetime import datetime, timezone

def run():
    # ID 8010404 ist Zerbst/Anhalt (Regio-Knoten)
    url = "https://v6.db.transport.rest/stops/8010404/departures?duration=600&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Wir nehmen alle Züge außer Busse
            if d.get('line', {}).get('product') == 'bus': 
                continue
            
            linie = d.get('line', {}).get('name', '').replace(" ", "")
            
            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            soll_z = soll.split('T')[1][:5]
            ist_z = ist.split('T')[1][:5]
            
            # Grund finden
            remarks = d.get('remarks', [])
            grund = " | ".join([rm.get('text', '') for rm in remarks if rm.get('type') == 'hint'][:1])

            res.append({
                "zeit": soll_z,
                "echte_zeit": ist_z,
                "linie": linie,
                "ziel": d.get('direction', 'Ziel')[:18],
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_z}" if ist_z != soll_z else ""),
                "grund": grund
            })
        
        # Falls die Liste immer noch leer ist, liegt es an der API
        if not res:
            res = [{"zeit": "--:--", "linie": "INFO", "ziel": "Warten auf DB Daten", "gleis": "-", "info": "Kein Zug"}]

        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump([{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15]}], f)

if __name__ == "__main__":
    run()
