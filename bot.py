import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    # Deutsche Zeit für den Stempel
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 1. Deine Station (Wannsee oder Zerbst)
        # Für Zerbst: 8010405 | Für Wannsee: 8010358
        station_id = "8010358" 
        
        # URL mit allen Parametern für maximale Infos
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=15&remarks=true&language=de"
        
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- VERBESSERTE REMARKS-LOGIK ---
            hinweise = []
            remarks = dep.get('remarks', [])
            
            for rm in remarks:
                # Wir nehmen jetzt 'hint' UND 'status' Nachrichten auf
                if rm.get('type') in ['hint', 'status']:
                    txt = rm.get('text', '').strip()
                    # Ignoriere Standard-Sätze wie "Fahrradmitnahme begrenzt" 
                    # um Platz für echte Gründe zu lassen
                    if txt and "Fahrrad" not in txt and txt not in hinweise:
                        hinweise.append(txt)
            
            grund = " | ".join(hinweise)
            
            delay = dep.get('delay')
            cancelled = dep.get('cancelled', False)
            
            # Textbau
            if cancelled:
                info_text = f"FÄLLT AUS! {grund}".strip()
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                # Falls ein Textgrund da ist, hänge ihn an die Minuten an
                info_text = f"+{minuten} Min: {grund}" if grund else f"+{minuten} Min"
            else:
                info_text = grund # Bauarbeiten etc. auch ohne Verspätung zeigen

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:12]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": "Fehler", "gleis": "-", "info": str(e)[:20]}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
