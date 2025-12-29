import requests, json
from datetime import datetime, timedelta, timezone

def hole_daten():
    jetzt = datetime.now(timezone.utc)
    u_zeit = (jetzt + timedelta(hours=1)).strftime("%H:%M")
    try:
        # Dynamische Suche nach Zerbst/Anhalt
        suche = requests.get("https://v6.db.transport.rest/locations?query=Zerbst/Anhalt&results=1", timeout=10).json()
        echte_id = suche[0]['id']
        r = requests.get(f"https://v6.db.transport.rest/stops/{echte_id}/departures?duration=480&results=15&remarks=true", timeout=15).json()
        res = []
        for d in r.get('departures', []):
            if d.get('line', {}).get('product') == 'bus': continue
            ist_w = d.get('when') or d.get('plannedWhen')
            soll_zeit = d.get('plannedWhen', ist_w).split('T')[1][:5]
            ist_zeit = ist_w.split('T')[1][:5]
            info = "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist_zeit}" if ist_zeit != soll_zeit else "")
            res.append({"zeit": soll_zeit, "echte_zeit": ist_zeit, "linie": d['line']['name'], "ziel": d['direction'][:18], "gleis": str(d.get('platform') or "-"), "info": info, "update": u_zeit})
        return res[:10]
    except: return []

if __name__ == "__main__":
    with open('zerbst.json', 'w', encoding='utf-8') as f: json.dump(hole_daten(), f, ensure_ascii=False, indent=4)
