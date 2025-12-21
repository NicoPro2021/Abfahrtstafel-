import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    station_id = "8010358" # 8010358 = Wannsee | 8010405 = Zerbst

    # Liste von verschiedenen API-Servern, die wir nacheinander probieren
    api_server = [
        f"https://v6.db.transport.rest/stops/{station_id}/departures?results=15&duration=120&remarks=true&language=de",
        f"https://v5.db.transport.rest/stops/{station_id}/departures?results=15&duration=120",
        f"https://db-v5.juliuste.de/stops/{station_id}/departures?results=15"
    ]

    data = None
    success_url = ""

    # Probiere alle Server nacheinander durch
    for url in api_server:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                success_url = url
                break # Erfolg! Schleife abbrechen
        except:
            continue

    if not data:
        return [{"zeit": "Err", "linie": "NOT", "ziel": "Offline", "gleis": "-", "info": "Alle Server down", "update": u_zeit}]

    # Ab hier die normale Verarbeitung der Daten
    departures = data.get('departures', [])
    if not departures and 'departures' not in data: # Falls die Struktur bei v5 anders ist
        departures = data if isinstance(data, list) else []

    fahrplan = []
    for dep in departures:
        try:
            # Zeit-Extraktion (v5 und v6 kompatibel)
            zeit_roh = dep.get('when') or dep.get('plannedWhen')
            if not zeit_roh: continue
            ist_zeit = zeit_roh.split('T')[1][:5]
            soll_zeit = dep.get('plannedWhen', zeit_roh).split('T')[1][:5]
            
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            ziel = dep.get('direction', 'Ziel')[:20]
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")

            # Hinweise extrahieren
            hinweise = []
            remarks = dep.get('remarks', [])
            if isinstance(remarks, list):
                for rm in remarks:
                    if isinstance(rm, dict) and rm.get('type') in ['hint', 'status']:
                        t = rm.get('text', '').strip()
                        if t and "Fahrrad" not in t and t not in hinweise:
                            hinweise.append(t)
            
            grund = " | ".join(hinweise)
            delay = dep.get('delay')
            
            if dep.get('cancelled'):
                info_text = "FÄLLT AUS!"
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                info_text = f"+{minuten} Min: {grund}" if grund else f"+{minuten} Min"
            else:
                info_text = grund

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })
        except:
            continue

    return fahrplan[:12]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
