import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitstempel für das Display
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    
    # STATION ID FÜR ZERBST/ANHALT
    station_id = "8010405" 
    
    # Abfrage der nächsten 120 Minuten
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=20&duration=120&remarks=true"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        departures = data.get('departures', [])
        fahrplan = []

        for dep in departures:
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Busse filtern (in Zerbst oft wichtig, damit nur Züge bleiben)
            if "Bus" in linie:
                continue

            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            ist_zeit = zeit_roh.split('T')[1][:5]
            ziel = dep.get('direction', 'Ziel')[:20]
            gleis = str(dep.get('platform') or "-")
            
            # --- VERSPÄTUNGS-LOGIK ---
            delay = dep.get('delay')
            info_text = ""
            
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            else:
                # Suche nach dem Grund in den 'remarks'
                rems = dep.get('remarks', [])
                grund = ""
                for rm in rems:
                    if rm.get('type') == 'warning':
                        # Kurze Zusammenfassung des Grundes holen
                        grund = rm.get('summary', "")
                        break
                
                if delay and delay >= 60:
                    minuten = int(delay/60)
                    # Kombiniere Verspätung und Grund
                    info_text = f"+{minuten} {grund}".strip()
                else:
                    info_text = grund

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach der Zeit, wann der Zug WIRKLICH kommt
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "API", "ziel": "Fehler", "gleis": "-", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
