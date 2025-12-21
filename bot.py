import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    try:
        # Station ID (Wannsee: 8010358 | Zerbst: 8010405)
        station_id = "8010358" 
        
        # Wir fragen nach einem großen Zeitraum (240 Min), um Lücken zu vermeiden
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=240&remarks=true&language=de"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        # Wir nehmen die Zeit direkt vom API-Server als Referenz ("jetzt")
        # Falls die API keine Zeit liefert, nehmen wir UTC
        jetzt_str = r.headers.get('Date')
        if jetzt_str:
            jetzt_ref = datetime.strptime(jetzt_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
        else:
            jetzt_ref = datetime.now(timezone.utc)

        # Deutsche Anzeigezeit für das Display
        u_zeit = (jetzt_ref + timedelta(hours=1)).strftime("%H:%M")
        
        fahrplan = []
        # Wir zeigen Züge, die ab JETZT fahren (minus 2 Min Puffer)
        puffer = jetzt_ref - timedelta(minutes=2)

        for dep in departures:
            zeit_str = dep.get('when')
            if not zeit_str: continue
            
            abfahrt_obj = datetime.fromisoformat(zeit_str.replace('Z', '+00:00'))
            
            # STRENGER FILTER: Abgelaufene Züge sofort raus
            if abfahrt_obj < puffer:
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = zeit_str.split('T')[1][:5]
            
            # Remarks sammeln
            hinweise = []
            for rm in dep.get('remarks', []):
                if rm.get('type') in ['hint', 'status']:
                    t = rm.get('text', '').strip()
                    if t and "Fahrrad" not in t and t not in hinweise:
                        hinweise.append(t)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            
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
                "update": u_zeit
            })

        # Nach ECHTER Zeit sortieren
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # Falls die Liste leer ist (z.B. nachts), zeigen wir eine Info an
        if not fahrplan:
             return [{"zeit": "--:--", "linie": "DB", "ziel": "Keine Zuege", "gleis": "-", "info": "Betriebspause", "update": u_zeit}]

        return fahrplan[:15]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
