import requests, json
from datetime import datetime, timezone

def run():
    # ID 8010404 ist Zerbst/Anhalt
    url = "https://v6.db.transport.rest/stops/8010404/departures?duration=600&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        res = []
        for d in departures:
            # Sicherheits-Check: Hat der Zug überhaupt Zeitdaten?
            soll_iso = d.get('plannedWhen') or d.get('when')
            if not soll_iso:
                continue # Überspringe Züge ohne Zeitangabe
            
            # Busse ausfiltern
            if d.get('line', {}).get('product') == 'bus':
                continue
            
            # Zeiten sicher extrahieren
            try:
                soll_z = soll_iso.split('T')[1][:5]
                ist_iso = d.get('when') or soll_iso
                ist_z = ist_iso.split('T')[1][:5]
            except (AttributeError, IndexError):
                continue

            # Grund/Remarks sicher sammeln
            remarks = d.get('remarks', [])
            grund_liste = []
            if isinstance(remarks, list):
                for rm in remarks:
                    if rm.get('type') == 'hint':
                        t = rm.get('text', '').strip()
                        if t and "Fahrrad" not in t:
                            grund_liste.append(t)
            
            grund = " | ".join(grund_liste[:1])

            res.append({
                "zeit": soll_z,
                "echte_zeit": ist_z,
                "linie": d.get('line', {}).get('name', '').replace(" ", ""),
                "ziel": d.get('direction', 'Ziel')[:18],
                "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_z}" if ist_z != soll_z else ""),
                "grund": grund
            })
        
        # Falls die Liste immer noch leer ist
        if not res:
            res = [{"zeit": "--:--", "linie": "INFO", "ziel": "Keine Züge aktuell", "gleis": "-", "info": "Fahrplan leer"}]

        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        print("Zerbst Bot: Datei erfolgreich geschrieben.")
            
    except Exception as e:
        # Fehlermeldung als Liste speichern, damit die Website nicht abstürzt
        error_res = [{"zeit": "ERR", "linie": "Bot", "ziel": "Fehler", "info": str(e)[:20]}]
        with open('zerbst.json', 'w', encoding='utf-8') as f:
            json.dump(error_res, f, ensure_ascii=False, indent=4)
        print(f"Fehler bei Zerbst: {e}")

if __name__ == "__main__":
    run()
