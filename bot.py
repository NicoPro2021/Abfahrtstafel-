import requests
import json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = jetzt.strftime("%H:%M")
    
    try:
        # 1. Zerbst ID holen (8010405)
        suche_url = "https://v6.db.transport.rest/locations?query=Zerbst&results=1"
        suche_res = requests.get(suche_url, timeout=10)
        echte_id = suche_res.json()[0]['id']
        
        # 2. Abfahrten mit 'remarks=true' abrufen, um Gründe zu erhalten
        url = f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=40&remarks=true"
        r = requests.get(url, timeout=15)
        data = r.json()
        departures = data.get('departures', [])
        
        fahrplan = []
        for dep in departures:
            ist_w = dep.get('when')
            if not ist_w: continue
            
            zug_zeit_obj = datetime.fromisoformat(ist_w.replace('Z', '+00:00'))
            if zug_zeit_obj < (jetzt - timedelta(minutes=1)):
                continue

            linie = dep.get('line', {}).get('name', '???').replace(" ", "")
            soll_w = dep.get('plannedWhen')
            soll_zeit = soll_w.split('T')[1][:5] if soll_w else "--:--"
            ist_zeit = ist_w.split('T')[1][:5]
            
            # --- NEU: GRÜNDE (REMARKS) EXTRAHIEREN ---
            remarks = dep.get('remarks', [])
            # Wir filtern nur wichtige 'hints' (Hinweise), die Text enthalten
            relevante_infos = [r.get('text') for r in remarks if r.get('type') == 'hint' and r.get('text')]
            grund_text = " | ".join(relevante_infos)
            
            # Info-Logik zusammenbauen
            cancelled = dep.get('cancelled', False)
            delay = dep.get('delay')
            
            if cancelled:
                info_text = f"FÄLLT AUS: {grund_text}" if grund_text else "FÄLLT AUS"
            elif delay and delay >= 300: # Ab 5 Min Verspätung
                minuten = int(delay / 60)
                info_text = f"+{minuten} Min: {grund_text}" if grund_text else f"+{minuten} Min"
            else:
                # Auch wenn pünktlich, gibt es manchmal wichtige Infos (Bauarbeiten etc.)
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

        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:10]

    except Exception as e:
        return [{"zeit": "Err", "linie": "Bot", "ziel": str(e)[:15], "gleis": "-", "info": "Error"}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
