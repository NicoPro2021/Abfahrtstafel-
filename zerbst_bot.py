import requests, json
from datetime import datetime, timezone

def run():
    # ID 8010404 = Zerbst/Anhalt (Sachsen-Anhalt)
    # Wir fragen explizit nach regionalen Zügen
    url = "https://v6.db.transport.rest/stops/8010404/departures?duration=480&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # In Zerbst fahren NUR RE13 und RB51. RE1, RE7 etc. haben hier nichts zu suchen.
            linie = d.get('line', {}).get('name', '').replace(" ", "")
            if not ("RE13" in linie or "RB51" in linie):
                continue
            
            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            # Gründe/Hinweise extrahieren
            remarks = d.get('remarks', [])
            grund_liste = [rm.get('text', '').strip() for rm in remarks if rm.get('type') == 'hint']
            grund = " | ".join(grund_liste[:2])
            
            soll_z = soll.split('T')[1][:5]
            ist_z = ist.split('T')[1][:5]

            res.append({
                "zeit": soll_z,
                "echte_zeit": ist_z,
                "linie": linie,
                "ziel": d.get('direction', 'Ziel')[:18],
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_z}" if ist_z != soll_z else ""),
                "grund": grund
            })
        
        # Falls die API mal wieder spinnt und nichts liefert:
        if not res:
            print("Keine RE13/RB51 gefunden. Prüfe API...")

        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"Zerbst/Anhalt erfolgreich aktualisiert.")
            
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    run()
