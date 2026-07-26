import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# ... (Deine STATIONS Konstante bleibt gleich) ...

def hole_station_daten_hafas(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    
    # Nutzung der DB Hafas API via transport.rest für Abfahrten
    url = f"https://v6.db.transport.rest/stops/{eva_id}/departures"
    
    params = {
        "duration": 120,      # Abfahrten der nächsten 120 Minuten
        "results": 40,        # Maximale Anzahl an Ergebnissen
        "bus": "true",        # WICHTIG: Busse (und damit SEV) einschließen!
        "regional": "true",
        "suburban": "true",
        "national": "true",
        "nationalExpress": "true",
        "language": "de"
    }
    
    verbindungen = []
    
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200: 
            return []
            
        data = res.json()
        departures = data.get("departures", [])
        
        for dep in departures:
            # Herausfiltern von Fahrten, die in der Vergangenheit liegen oder komplett storniert sind
            if dep.get("cancelled"):
                continue
                
            def format_iso_time(iso_str):
                if not iso_str: return "--:--"
                clean_str = iso_str.split("+")[0].split("Z")[0]
                dt = datetime.strptime(clean_str[:16], "%Y-%m-%dT%H:%M")
                return dt.strftime("%H:%M")
            
            p_time = format_iso_time(dep.get("plannedWhen"))
            e_time = format_iso_time(dep.get("when") or dep.get("plannedWhen"))
            
            # Verspätung berechnen
            delay = dep.get("delay")
            if delay and delay > 0:
                info = f"+{int(delay/60)}"
            else:
                info = "pünktlich"
                
            # SEV-Check: Wenn es ein Bus ist, wird das oft im Namen oder in der Linie vermerkt
            line_name = dep.get("line", {}).get("name", "Unbekannt")
            if "SEV" in line_name.upper() or "ERSATZ" in line_name.upper():
                info = f"SEV ({info})"
                
            ziel = dep.get("direction", "Unbekannt")[:20]
            gleis = dep.get("platform") or dep.get("plannedPlatform") or "-"
            
            # Begründung/Bemerkungen auslesen (falls vorhanden)
            remarks = dep.get("remarks", [])
            begruendung = " | ".join([r.get("summary", "") for r in remarks if r.get("type") == "status" and r.get("summary")])
            
            verbindungen.append({
                "zeit": p_time,
                "echte_zeit": e_time,
                "linie": line_name,
                "ziel": ziel,
                "gleis": gleis,
                "info": info,
                "begruendung": begruendung,
                "update": jetzt.strftime("%H:%M")
            })
            
        # Optional: Nach Zeit sortieren
        verbindungen.sort(key=lambda x: x['zeit'])
        return verbindungen
        
    except Exception as e:
        print(f"Fehler bei Station {eva_id}: {e}")
        return []

def verarbeite_station(item):
    name, eva_id = item
    # Hier rufen wir nun die neue Hafas-Funktion auf
    daten = hole_station_daten_hafas(eva_id)
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
