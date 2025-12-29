import requests, json
# Ändere hier die ID je nach Station (z.B. Zerbst: 8010390)
STATION_ID = "8010390" 
DATEI_NAME = "zerbst.json"

def run():
    url = f"https://v6.db.transport.rest/stops/{STATION_ID}/departures?duration=480&results=15&remarks=true"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        res = []
        for d in data.get('departures', []):
            if d.get('line', {}).get('product') == 'bus': continue
            soll = d.get('plannedWhen') or d.get('when')
            ist = d.get('when') or soll
            if not soll: continue
            
            # Grund finden
            grund = " | ".join([rm.get('text','') for rm in d.get('remarks',[]) if rm.get('type')=='hint'][:2])
            
            res.append({
                "zeit": soll.split('T')[1][:5],
                "echte_zeit": ist.split('T')[1][:5],
                "linie": d.get('line',{}).get('name','').replace(" ",""),
                "ziel": d.get('direction','')[:18],
                "gleis": str(d.get('platform') or "-"),
                "info": "FÄLLT AUS" if d.get('cancelled') else (f"ca. {ist.split('T')[1][:5]}" if ist != soll else ""),
                "grund": grund
            })
        with open(DATEI_NAME, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
    except:
        with open(DATEI_NAME, 'w') as f: json.dump([], f)

if __name__ == "__main__":
    run()
