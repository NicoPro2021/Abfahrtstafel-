import requests
import json
from datetime import datetime, timedelta

def hole_daten():
    # Aktuelle Zeit (für den Filter)
    jetzt = datetime.now()
    u_zeit = jetzt.strftime("%H:%M")
    
    try:
        # Schritt 1: ID für Zerbst finden (8010403)
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # Schritt 2: Abfahrten laden (duration=300 heißt die nächsten 5 Stunden)
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=300&results=20"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            # Tatsächliche Zeit (Ist) zum Vergleichen nutzen
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Umwandeln in Python-Zeitobjekt zum Filtern
            # Beispiel: 2024-05-20T14:30:00+02:00
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            
            # WICHTIG: Züge die vor mehr als 2 Minuten abgefahren sind, löschen
            if zug_zeit_obj < (jetzt - timedelta(minutes=2)):
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            if any(x in linie for x in ["ICE", "IC", "RT"]): continue
            
            # Geplante Zeit (Soll)
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # Verspätung/Info
            cancelled = dep.get('cancelled', False)
            if cancelled:
                info_text = "fällt aus"
            else:
                delay = dep.get('delay') # Sekunden
                if delay is not None and delay > 0:
                    info_text = f"+{int(delay / 60)}"
                else:
                    info_text = "" # Leer lassen für pünktlich (sieht sauberer aus)

            ziel = dep.get('direction', 'Ziel unbekannt')
            gleis = str(dep.get('platform') or dep.get('plannedPlatform') or "-")
            
            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel[:20], # Etwas mehr Platz für das Ziel
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        # Nach Zeit sortieren (falls die API sie durcheinander wirft)
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:8]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
