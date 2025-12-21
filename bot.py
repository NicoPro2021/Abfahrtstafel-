import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # 1. Zeitmanagement
    jetzt = datetime.now(timezone.utc)
    # Deutsche Zeit für den "Update"-Stempel im Display
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 2. Bahnhofs-ID (Zerbst: 8010405 | Wannsee: 8010358)
        # Ändere diese ID je nachdem, welchen Bahnhof du sehen willst!
        station_id = "8010405" 
        
        # API-Abfrage mit allen Details (remarks=true für Verspätungsgründe)
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=120&results=20&remarks=true&language=de"
        
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        
        # --- SICHERHEITS-PUFFER ---
        # Wir zeigen Züge bis zu 5 Minuten nach ihrer Abfahrt noch an,
        # damit die Liste bei Zeit-Synchronisationsfehlern nicht leer wird.
        puffer_zeit = jetzt - timedelta(minutes=5)

        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Zeit-Objekt der Abfahrt erstellen
            abfahrt_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # --- FILTER: Abgelaufene Züge rauswerfen ---
            if abfahrt_obj < puffer_zeit:
                continue

            # Daten-Extraktion
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- GRÜNDE (REMARKS) SAMMELN ---
            hinweise = []
            remarks = dep.get('remarks', [])
            for rm in remarks:
                if rm.get('type') in ['hint', 'status']:
                    txt = rm.get('text', '').strip()
                    # Unnötige Infos filtern, um Platz im Ticker zu sparen
                    if txt and "Fahrrad" not in txt and txt not in hinweise:
                        hinweise.append(txt)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            cancelled = dep.get('cancelled', False)
            
            # Info-Text Logik
            if cancelled:
                info_text = f"FÄLLT AUS! {grund}".strip()
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                info_text = f"+{minuten} Min: {grund}" if grund else f"+{minuten} Min"
            else:
                info_text = grund # Bauarbeiten etc.

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach der tatsächlichen Zeit
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # Falls wirklich gar nichts mehr fährt (z.B. nachts)
        if not fahrplan:
            fahrplan.append({
                "zeit": "--:--",
                "echte_zeit": "23:59",
                "linie": "INFO",
                "ziel": "Keine Abfahrten",
                "gleis": "-",
                "info": "Aktuell kein Betrieb",
                "update": u_zeit
            })

        return fahrplan[:15] # Die nächsten 15 Einträge zurückgeben

    except Exception as e:
        # Fehler-Eintrag für das Display
        return [{"zeit": "Err", "linie": "Bot", "ziel": "API Fehler", "gleis": "-", "info": str(e)[:20], "update": "--:--"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
