import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    try:
        # Station ID (Wannsee: 8010358 | Zerbst: 8010405)
        station_id = "8010358" 
        
        # Wir fragen die API nach Abfahrten (results=15 holt die nächsten 15)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=15&remarks=true&language=de"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        # Zeitstempel für das Display-Update
        u_zeit = datetime.now(timezone(timedelta(hours=1))).strftime("%H:%M")
        
        fahrplan = []

        for dep in departures:
            zeit_str = dep.get('when')
            if not zeit_str: continue
            
            # Wir extrahieren die Zeit einfach als Text, ohne strengen Filter
            # Das verhindert, dass die Liste durch Zeitzonen-Fehler leer wird
            ist_zeit = zeit_str.split('T')[1][:5]
            
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else ist_zeit
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # Remarks / Gründe sammeln
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

        # Wenn trotzdem leer, dann liegt es an der API
        if not fahrplan:
             return [{"zeit": "--:--", "linie": "DB", "ziel": "Keine Daten", "gleis": "-", "info": "API leer", "update": u_zeit}]

        return fahrplan

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20], "update": "--:--"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
