import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    # Aktuelle Zeit für den Filter
    jetzt = datetime.now(timezone.utc)
    # Zeitstempel für das Display (Deutsche Zeit)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    
    try:
        # 1. ID für Zerbst/Anhalt sicherstellen
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # 2. Abfahrten laden - WICHTIG: remarks=true für die Verspätungsgründe!
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=20&remarks=true"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            # Vergangene Züge ignorieren
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            if zug_zeit_obj < (jetzt - timedelta(minutes=5)):
                continue

            # Basis-Infos
            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- TEXTGRÜNDE (REMARKS) AUSLESEN ---
            remarks = dep.get('remarks', [])
            texte = []
            for rm in remarks:
                # Wir filtern nur echte Text-Hinweise
                if rm.get('type') == 'hint':
                    t = rm.get('text', '').strip()
                    if t and t not in texte: # Doppelte Texte vermeiden
                        texte.append(t)
            
            grund = " | ".join(texte)
            
            # Info-Feld zusammenbauen
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay') # Verspätung in Sekunden
            
            if cancelled:
                info_text = f"FÄLLT AUS: {grund}" if grund else "FÄLLT AUS"
            elif delay and delay >= 60:
                minuten = int(delay / 60)
                info_text = f"+{minuten} Min: {grund}" if grund else f"+{minuten} Min"
            else:
                info_text = grund # Falls pünktlich, aber Bauinfos da sind

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": dep.get('direction', 'Ziel unbekannt')[:20],
                "gleis": str(dep.get('platform') or dep.get('plannedPlatform') or "-"),
                "info": info_text,
                "update": u_zeit
            })

        # Sortieren nach tatsächlicher Abfahrt
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Fehler"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
