import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitstempel für das Update (Zerbst Zeit)
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    url = "https://v6.db.transport.rest/stops/8010405/departures?results=15&duration=240"
    
    try:
        # User-Agent hilft, damit die Bahn-API uns nicht blockiert
        headers = {'User-Agent': 'Zerbst-Monitor-v2'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            # Filtert Busse aus (wie RUF452), damit nur Züge erscheinen
            if "Bus" in linie or "RUF" in linie: 
                continue 

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            soll_zeit = zeit_roh.split('T')[1][:5]
            ziel = dep.get('direction', 'Ziel')[:18]
            gleis = str(dep.get('platform') or "-")
            
            delay = dep.get('delay')
            info = f"+{int(delay/60)}" if delay and delay >= 60 else ""

            fahrplan.append({
                "zeit": soll_zeit, 
                "linie": linie, 
                "ziel": ziel, 
                "gleis": gleis, 
                "info": info, 
                "update": u_zeit
            })
        return fahrplan[:10]
    except Exception as e:
        print(f"Fehler beim Abruf: {e}")
        return None # Gibt bei Fehler gar nichts zurück

if __name__ == "__main__":
    neue_daten = hole_daten()
    
    # WICHTIG: Nur speichern, wenn wir ECHTE Daten bekommen haben!
    if neue_daten is not None and len(neue_daten) > 0:
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(neue_daten, f, ensure_ascii=False, indent=4)
        print("Daten erfolgreich aktualisiert.")
    else:
        print("Abbruch: Keine gültigen Daten empfangen. daten.json bleibt unverändert.")
