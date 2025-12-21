import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Zeitstempel für das Display
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    station_id = "8010358" # 8010358 = Wannsee | 8010405 = Zerbst
    
    # VERSUCH 1: Mit Gründen (Remarks)
    try:
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=10&duration=60&remarks=true&language=de"
        r = requests.get(url, timeout=10)
        
        # Wenn der Server 500 liefert, springen wir sofort in den Except-Block
        r.raise_for_status()
        data = r.json()
    except Exception:
        # VERSUCH 2: Notfall-Modus ohne Gründe (sehr stabil)
        try:
            url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&duration=120&remarks=false"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return [{"zeit": "Err", "linie": "API", "ziel": "Down", "gleis": "-", "info": "Server Offline", "update": u_zeit}]

    departures = data.get('departures', [])
    fahrplan = []

    for dep in departures:
        try:
            # Zeit-Extraktion
            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            ist_zeit = zeit_roh.split('T')[1][:5]
            
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Hinweise (nur wenn in Versuch 1 erfolgreich)
            hinweise = []
            for rm in dep.get('remarks', []):
                if rm.get('type') in ['hint', 'status']:
                    t = rm.get('text', '').strip()
                    if t and "Fahrrad" not in t and t not in hinweise:
                        hinweise.append(t)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            elif delay and delay >= 60:
                info_text = f"+{int(delay/60)} Min: {grund}" if grund else f"+{int(delay/60)} Min"
            else:
                info_text = grund

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })
        except:
            continue

    return fahrplan if fahrplan else [{"zeit": "Wait", "linie": "DB", "ziel": "Keine Züge", "gleis": "-", "info": "", "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
