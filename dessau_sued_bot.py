import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    try:
        suche_url = "https://v6.db.transport.rest/locations?query=Dessau Süd&results=1"
        suche_data = requests.get(suche_url, timeout=10).json()
        station_id = suche_data[0]['id']
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures?duration=60&results=100&remarks=true"
        r = requests.get(url, timeout=15).json()
        res = []
        for d in r.get('departures', []):
            try:
                line = d.get('line', {})
                name = line.get('name', '').replace(" ", "")
                ziel = d.get('direction', '')
                soll_raw = d.get('plannedWhen')
                ist_raw = d.get('when') or soll_raw
                if not soll_raw: continue
                soll_dt = datetime.fromisoformat(soll_raw.replace('Z', '+00:00'))
                ist_dt = datetime.fromisoformat(ist_raw.replace('Z', '+00:00'))
                diff = int((ist_dt - soll_dt).total_seconds() / 60)
                info_feld = "FÄLLT AUS" if d.get('cancelled') else (f"+{diff}" if diff > 0 else "")
                res.append({
                    "zeit": soll_dt.strftime("%H:%M"), "echte_zeit": ist_dt.strftime("%H:%M"), 
                    "linie": name, "ziel": ziel[:18], 
                    "gleis": str(d.get('platform') or d.get('plannedPlatform') or "-"), 
                    "info": info_feld, 
                    "grund": " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:1]),
                    "update": u_zeit
                })
            except: continue
        return res
    except: return []

if __name__ == "__main__":
    daten = hole_daten()
    with open('dessau_sued.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
