import requests, json
from datetime import datetime, timezone

def run():
    # ID 8010405 ist der Knotenpunkt Zerbst/Anhalt
    url = "https://v6.db.transport.rest/stops/8010405/departures?duration=480&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            linie = d.get('line', {}).get('name', '').replace(" ", "")
            
            # WICHTIG: Nur RE13 und RE14 (und RB51 als Backup, falls Linie umbenannt)
            if not any(x in linie for x in ["RE13", "RE14", "RB51"]):
                continue
            
            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            soll_z = soll.split('T')[1][:5]
            ist_z = ist.split('T')[1][:5]
            
            # Grund finden (Verspätungen etc.)
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
        
        # Falls leer, schreiben wir eine Info-Zeile zur Diagnose
        if not res:
            res = [{"zeit": "---", "linie": "RE13/14", "ziel": "Keine Züge im Plan", "gleis": "-", "info": "Check"}]

        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"Zerbst Bot: {len(res)} RE13/RE14 Züge gefunden.")
            
    except Exception as e:
        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump([{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:15]}], f)

if __name__ == "__main__":
    run()
