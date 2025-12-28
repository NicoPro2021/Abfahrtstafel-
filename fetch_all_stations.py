import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- STATIONSLISTE MIT KORREKTEN IDs ---
stationen = [
    {"name": "zerbst", "id": "8013313"},
    {"name": "rodleben", "id": "8012808"},
    {"name": "rosslau", "id": "8010298"}, # Roßlau (Elbe)
    {"name": "dessau_hbf", "id": "8010077"},
    {"name": "dessau_sued", "id": "8011384"},
    {"name": "Magdeburg_Hbf", "id": "8010224"},
    {"name": "magdeburg_neustadt", "id": "8010226"},
    {"name": "magdeburg_herrenkrug", "id": "8011910"},
    {"name": "leipzig_hbf", "id": "8010205"}
]

def hole_daten(station_id, station_name):
    jetzt = datetime.now(timezone.utc)
    # Wir fragen 12 Stunden (720 Min) ab, um sicherzugehen, dass wir Züge finden
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=720&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status() # Prüft ob die Webseite erreichbar ist
        data = r.json()
        departures = data.get('departures', [])
        
        if not departures:
            print(f"Warnung: Keine Abfahrten für {station_name} gefunden.")
            return []

        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # Filter: Nur Züge anzeigen, die noch nicht weg sind (Toleranz 2 Min)
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)): continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay', 0)
            
            info_text = ""
            if cancelled:
                info_text = "FÄLLT AUS"
            elif delay and delay >= 60:
                info_text = f"+{int(delay / 60)} Min"

            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text
            })

        # Nach Zeit sortieren
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:12]

    except Exception as e:
        print(f"KRITISCHER FEHLER bei {station_name}: {e}")
        return None

if __name__ == "__main__":
    for st in stationen:
        print(f"Update läuft für: {st['name']} (ID: {st['id']})")
        daten = hole_daten(st['id'], st['name'])
        
        if daten is not None:
            # Datei schreiben (auch wenn die Liste leer ist, um alte Daten zu löschen)
            with open(f"{st['name']}.json", 'w', encoding='utf-8') as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
            print(f"Erfolg: {len(daten)} Züge in {st['name']}.json gespeichert.")
        else:
            print(f"Abbruch: {st['name']}.json wurde nicht aktualisiert.")
