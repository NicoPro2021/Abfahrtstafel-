import requests, json
from datetime import datetime, timezone

def run():
    # Wir nutzen die ID 8010391 für Zerbst/Anhalt
    url = "https://v6.db.transport.rest/stops/8010391/departures?duration=480&results=15&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Filter für Züge (RE13, RB51) - keine Busse
            product = d.get('line', {}).get('product', '')
            if product == 'bus': continue
            
            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            # Grund finden (Verspätungsgrund)
            grund = " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:2])
            
            soll_z = soll.split('T')[1][:5]
            ist_z = ist.split('T')[1][:5]

            res.append({
                "zeit": soll_z,
                "echte_zeit": ist_z,
                "linie": d.get('line',{}).get('name','').replace(" ",""),
                "ziel": d.get('direction','')[:18],
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_z}" if ist_z != soll_z else ""),
                "grund": grund
            })
        
        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"Zerbst (Anhalt) erfolgreich geladen: {len(res)} Züge.")
            
    except Exception as e:
        print(f"Fehler bei Zerbst: {e}")

if __name__ == "__main__":
    run()
