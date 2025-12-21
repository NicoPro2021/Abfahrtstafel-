import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    # Deutsche Zeit für den Update-Stempel
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # Zerbst/Anhalt ID
        station_id = "8010405" 
        
        # URL mit remarks=true (WICHTIG!)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=10&remarks=true&language=de"
        
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Basis-Daten
            ist_w = dep.get('when')
            if not ist_w: continue
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- INFO-LOGIK FÜR GRÜNDE ---
            hinweise = []
            remarks = dep.get('remarks', [])
            
            for rm in remarks:
                # Wir suchen nur Texte vom Typ 'hint' (das sind die Verspätungsgründe)
                if rm.get('type') == 'hint':
                    txt = rm.get('text', '').strip()
                    if txt and txt not in hinweise:
                        hinweise.append(txt)
            
            grund = " | ".join(hinweise)
            
            delay = dep.get('delay') # Verspätung in Sekunden
            cancelled = dep.get('cancelled', False)
            
            # Text zusammenbauen
            if cancelled:
                info_text = f"FÄLLT AUS! {grund}".strip()
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                # Hier wird die Verspätung mit dem Grund verknüpft
                info_text = f"+{minuten} Min: {grund}" if grund else f"+{minuten} Min"
            else:
                info_text = grund # Auch bei 0 Min Verspätung Gründe zeigen (z.B. Bauarbeiten)

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach der echten Zeit
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Fehler"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
