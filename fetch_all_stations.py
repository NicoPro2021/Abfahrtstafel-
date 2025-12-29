import requests
import json
from datetime import datetime, timedelta, timezone

# --- KONFIGURATION: IDs STAND DEZEMBER 2025 ---
stationen = [
    {"name": "zerbst", "id": "8010391"},           # Zerbst/Anhalt (Sachsen-Anhalt)
    {"name": "rodleben", "id": "8012808"},         # Rodleben
    {"name": "rosslau", "id": "8010298"},          # Roßlau (Elbe)
    {"name": "dessau_hbf", "id": "8010077"},       # Dessau Hbf
    {"name": "dessau_sued", "id": "8011384"},      # Dessau Süd
    {"name": "magdeburg_hbf", "id": "8010224"},    # Magdeburg Hbf
    {"name": "magdeburg_neustadt", "id": "8010226"},
    {"name": "magdeburg_herrenkrug", "id": "8011910"},
    {"name": "leipzig_hbf", "id": "8010205"}
]

def hole_daten(station_id, station_name):
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M") # Update-Zeit für die Anzeige
    
    # URL mit duration=600 (10 Stunden) für weite Voraussicht
    url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=600&results=20&remarks=true"
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # FILTER: Nur Züge, keine Busse
            if dep.get('line', {}).get('product') == 'bus':
                continue

            ist_w = dep.get('when')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            # Filter: Züge die mehr als 2 Minuten weg sind ignorieren
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)): continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # Remarks / Infos sammeln (z.B. Gleiswechsel, Baustellen)
            remarks = dep.get('remarks', [])
            texte = []
            for rm in remarks:
                if rm.get('type') == 'hint':
                    t = rm.get('text', '').strip()
                    if t and t not in texte: texte.append(t)
            
            grund = " | ".join(texte)
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay') # in Sekunden
            
            info_text = ""
            if cancelled:
                info_text = "FÄLLT AUS"
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                info_text = f"ca. {ist_zeit}" # Wir schreiben die neue Zeit in die Info
            else:
                info_text = grund[:30] # Kurze Info falls vorhanden

            fahrplan.append({
                "zeit": soll_zeit, 
                "echte_zeit": ist_zeit if ist_zeit != soll_zeit else "", 
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:18],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach tatsächlicher Abfahrt
        fahrplan.sort(key=lambda x: x['zeit'])
        return fahrplan[:12]

    except Exception as e:
        print(f"Fehler bei {station_name}: {e}")
        return []

if __name__ == "__main__":
    for st in stationen:
        print(f"Verarbeite: {st['name']}...")
        ergebnis = hole_daten(st['id'], st['name'])
        
        # Speichern als individuelle JSON Datei
        filename = f"{st['name']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(ergebnis, f, ensure_ascii=False, indent=4)
