import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    try:
        # 1. Station ID (8010358 ist Berlin-Wannsee, 8010405 ist Zerbst)
        # Überprüfe bitte, ob diese ID für deinen Teststandort korrekt ist!
        station_id = "8010358" 
        
        # 2. Die Anfrage: Wir nehmen einfach die nächsten 15 Ergebnisse
        # Ohne Zeitfilter, ohne Duration-Tricks
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&remarks=true&language=de"
        
        r = requests.get(url, timeout=15)
        r.raise_for_status() # Fehler werfen, falls API nicht erreichbar
        data = r.json()
        departures = data.get('departures', [])
        
        # Update-Zeit für dein Display (Berlin Zeit)
        u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
        
        fahrplan = []

        for dep in departures:
            # Zeit einfach als Text ausschneiden (Format: 2024-05-20T18:45:00...)
            # Wir nehmen nur die Zeichen von Stelle 11 bis 16 für die Uhrzeit
            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            ist_zeit = zeit_roh.split('T')[1][:5]
            
            soll_roh = dep.get('plannedWhen')
            soll_zeit = soll_roh.split('T')[1][:5] if soll_roh else ist_zeit
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            
            # --- Gründe/Remarks sammeln ---
            hinweise = []
            for rm in dep.get('remarks', []):
                if rm.get('type') in ['hint', 'status']:
                    t = rm.get('text', '').strip()
                    # Nur wichtige Texte, keine Fahrrad-Infos
                    if t and "Fahrrad" not in t and t not in hinweise:
                        hinweise.append(t)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            
            # Info-Text zusammenbauen
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

        # Falls die Liste immer noch leer ist, liegt es an der ID
        if not fahrplan:
             return [{"zeit": "Err", "linie": "ID?", "ziel": "Keine Daten", "gleis": "-", "info": f"ID {station_id} prüfen", "update": u_zeit}]

        return fahrplan

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20], "update": "--:--"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
