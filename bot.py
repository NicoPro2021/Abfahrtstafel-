import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # 1. Aktuelle Zeit in UTC holen
    jetzt_utc = datetime.now(timezone.utc)
    # Zeitstempel für das Display (Berlin Zeit)
    update_zeit = (jetzt_utc + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # Deine Station (Wannsee: 8010358 | Zerbst: 8010405)
        station_id = "8010358" 
        
        # API Abfrage
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&remarks=true&language=de"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        
        # --- DER FILTER ---
        # Wir lassen nur Züge zu, die JETZT oder in der ZUKUNFT abfahren.
        # Ein Puffer von 1 Minute ist okay, falls man gerade am Bahnsteig steht.
        puffer = jetzt_utc - timedelta(minutes=1)

        for dep in departures:
            zeit_str = dep.get('when')
            if not zeit_str: continue
            
            abfahrt_obj = datetime.fromisoformat(zeit_str.replace('Z', '+00:00'))
            
            # Wenn der Zug schon abgefahren ist -> Überspringen
            if abfahrt_obj < puffer:
                continue

            # Daten extrahieren
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = zeit_str.split('T')[1][:5]
            
            # Infos/Gründe sammeln
            hinweise = []
            for rm in dep.get('remarks', []):
                if rm.get('type') in ['hint', 'status']:
                    t = rm.get('text', '').strip()
                    if t and "Fahrrad" not in t and t not in hinweise:
                        hinweise.append(t)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            
            # Info-Text bauen
            if dep.get('cancelled'):
                info_text = f"FÄLLT AUS! {grund}".strip()
            elif delay and delay >= 60:
                info_text = f"+{int(delay/60)} Min: {grund}" if grund else f"+{int(delay/60)} Min"
            else:
                info_text = grund

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": update_zeit
            })

        # --- SORTIERUNG ---
        # Wichtig: Wir sortieren nach der ECHTEN Zeit (inkl. Verspätung)
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        return fahrplan[:15] # Nur die nächsten 15 Züge

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
