import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # WICHTIG: Wir nutzen die aktuelle UTC-Zeit für den Vergleich
    jetzt = datetime.now(timezone.utc)
    # Deutsche Zeit für den Update-Stempel (+1h oder +2h je nach Sommerzeit)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # Bahnhofs-ID (Beispiel Wannsee: 8010358 / Zerbst: 8010405)
        station_id = "8010358" 
        
        # Wir holen Daten für die nächsten 120 Minuten
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&remarks=true&language=de"
        
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Umwandlung der Abfahrtszeit in ein Python-Zeitobjekt
            abfahrt_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # --- DER FILTER: Nur Züge, die JETZT oder in der Zukunft fahren ---
            # Wir erlauben 0 Minuten Puffer. Sobald die Zeit um ist, fliegt der Zug raus.
            if abfahrt_obj < jetzt:
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # Remarks/Gründe sammeln
            hinweise = []
            remarks = dep.get('remarks', [])
            for rm in remarks:
                if rm.get('type') in ['hint', 'status']:
                    txt = rm.get('text', '').strip()
                    if txt and "Fahrrad" not in txt and txt not in hinweise:
                        hinweise.append(txt)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            cancelled = dep.get('cancelled', False)
            
            if cancelled:
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
                "update": u_zeit
            })

        # Nach der tatsächlichen Zeit sortieren (wichtig bei Verspätungen!)
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # Nur die nächsten 10-15 Züge speichern
        return fahrplan[:15]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
