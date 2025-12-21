import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    try:
        # Station ID (Wannsee: 8010358 | Zerbst: 8010405)
        station_id = "8010358" 
        
        # RADIKALE KÜRZUNG: Nur 10 Ergebnisse, kurzer Zeitraum (60 Min)
        # Das verhindert den 500 Server Error
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=10&duration=60&remarks=true&language=de"
        
        r = requests.get(url, timeout=10)
        # Wenn der Server 500 meldet, versuchen wir es ohne Remarks (als Backup)
        if r.status_code == 500:
            url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=10"
            r = requests.get(url, timeout=10)
        
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
        fahrplan = []

        for dep in departures:
            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            
            # Zeit extrahieren
            ist_zeit = zeit_roh.split('T')[1][:5]
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Hinweise sammeln (nur wenn vorhanden)
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

        return fahrplan if fahrplan else [{"zeit": "Wait", "linie": "DB", "ziel": "Keine Zuege", "gleis": "-", "info": "", "update": u_zeit}]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "API Down", "gleis": "-", "info": str(e)[:15], "update": "--:--"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
