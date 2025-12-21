import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Aktuelle Zeit in UTC für den API-Vergleich
    jetzt = datetime.now(timezone.utc)
    # Anzeige-Zeit für das "Update"-Feld im JSON
    u_zeit = jetzt.astimezone(timezone(timedelta(hours=1))).strftime("%H:%M")
    
    try:
        # 1. Bahnhofs-ID für Zerbst holen (8010405)
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # 2. Abfahrten abrufen (remarks=true ist der Schlüssel für die Gründe!)
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=40&remarks=true"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Zeit-Objekt für Filterung (keine Züge aus der Vergangenheit)
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            if zug_zeit_obj < (jetzt - timedelta(minutes=5)):
                continue

            # Daten extrahieren
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- INFO-LOGIK (GRÜNDE FINDEN) ---
            remarks = dep.get('remarks', [])
            hinweise = []
            
            for r_item in remarks:
                # Wir nehmen nur Hinweise (hints), keine Icons oder Betreiber-Infos
                if r_item.get('type') == 'hint':
                    text = r_item.get('text', '').strip()
                    # Dubletten vermeiden (Bahn schickt oft "Bauarbeiten" mehrfach)
                    if text and text not in hinweise:
                        hinweise.append(text)
            
            # Alle gefundenen Gründe mit einem Strich verbinden
            grund_text = " | ".join(hinweise)
            
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay') # Verspätung in Sekunden
            
            if cancelled:
                info_text = f"FÄLLT AUS: {grund_text}" if grund_text else "FÄLLT AUS"
            elif delay and delay >= 60: # Ab 1 Minute Verspätung anzeigen
                minuten = int(delay / 60)
                info_text = f"+{minuten} Min: {grund_text}" if grund_text else f"+{minuten} Min"
            else:
                # Auch bei pünktlichen Zügen wichtige Infos (z.B. Bauarbeiten) mitschicken
                info_text = grund_text 

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        # Sortierung nach der tatsächlichen Zeit
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        
        # Die nächsten 10 Abfahrten zurückgeben
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Fehler beim Laden"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
