import requests, json
from datetime import datetime, timezone

def run():
    # ID 8010405 ist DEFINITIV Zerbst/Anhalt (Strecke Magdeburg-Dessau-Leipzig)
    url = "https://v6.db.transport.rest/stops/8010405/departures?duration=480&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Filter: Nur Züge (RE13, RB51)
            product = d.get('line', {}).get('product', '')
            if product == 'bus': continue
            
            # Ziel-Check: Fährt der Zug in die richtige Region?
            ziel = d.get('direction', '')
            # Zerbst hat Züge nach Magdeburg, Leipzig, Dessau, Bitterfeld, Wittenberg
            region_check = ["Magdeburg", "Leipzig", "Dessau", "Bitterfeld", "Wittenberg", "Güterglück"]
            if not any(stadt in ziel for stadt in region_check):
                continue

            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            # Verspätungsgründe (Remarks) sammeln
            remarks = d.get('remarks', [])
            grund_liste = []
            for rm in remarks:
                if rm.get('type') == 'hint':
                    txt = rm.get('text', '').strip()
                    if txt and "Gleis" not in txt and "Fahrrad" not in txt:
                        grund_liste.append(txt)
            
            grund = " | ".join(grund_liste[:2])
            
            soll_z = soll.split('T')[1][:5]
            ist_z = ist.split('T')[1][:5]

            res.append({
                "zeit": soll_z,
                "echte_zeit": ist_z,
                "linie": d.get('line',{}).get('name', '').replace(" ", ""),
                "ziel": ziel[:18],
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_z}" if ist_z != soll_z else ""),
                "grund": grund
            })
        
        # Sortieren nach Zeit
        res.sort(key=lambda x: x['zeit'])
        
        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print(f"Zerbst/Anhalt geladen: {len(res)} Züge gefunden.")
            
    except Exception as e:
        print(f"Fehler bei Zerbst: {e}")

if __name__ == "__main__":
    run()
