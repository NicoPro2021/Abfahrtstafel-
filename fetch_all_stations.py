import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN (Für transport.rest eigentlich nicht mehr nötig, aber ich lasse sie für dich drin)
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8098205", "zerbst": "8013389",
    "dessau_hbf": "8010077", "rosslau": "8010302", "rodleben": "8012777",
    "bitterfeld": "8010050", "wolfen": "8013335", "magdeburg_herrenkrug": "8013455", "bad_belzig": "8010031", "berlin_hbf": "8011160", "brandenburg_hbf": "8010060",
    "biederitz": "8010047", "dessau_sued": "8011361", "gommern": "8011673", "magdeburg_neustadt": "8010226", "pretzier_altm": "8012673", "wusterwitz": "8013365", 
    "gueterglueck": "8010154", "wittenberge": "8010382", "berlin_hbf-tief": "8098160"
}

def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    
    # HAFAS API zieht Züge UND Busse (SEV)
    url = f"https://v6.db.transport.rest/stops/{eva_id}/departures"
    params = {
        "duration": 120,      
        "results": 40,        
        "bus": "true",        # WICHTIG FÜR SEV!
        "regional": "true",
        "suburban": "true",
        "national": "true",
        "nationalExpress": "true",
        "language": "de"
    }
    
    verbindungen = []
    
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            departures = res.json().get("departures", [])
            
            for dep in departures:
                def format_iso_time(iso_str):
                    if not iso_str: return "--:--"
                    clean_str = iso_str.split("+")[0].split("Z")[0]
                    dt = datetime.strptime(clean_str[:16], "%Y-%m-%dT%H:%M")
                    return dt.strftime("%H:%M")
                
                p_time_str = dep.get("plannedWhen")
                e_time_str = dep.get("when") or p_time_str
                
                if not p_time_str: 
                    continue
                    
                p_time = format_iso_time(p_time_str)
                e_time = format_iso_time(e_time_str)
                
                # FÄLLT AUS oder Verspätung berechnen
                is_cancelled = dep.get("cancelled", False)
                delay = dep.get("delay")
                
                if is_cancelled:
                    info = "FÄLLT AUS"
                elif delay and delay > 0:
                    info = f"+{int(delay/60)}"
                else:
                    info = "pünktlich"
                    
                # SEV Check
                line_name = dep.get("line", {}).get("name", "Unbekannt")
                if ("SEV" in line_name.upper() or "ERSATZ" in line_name.upper()) and not is_cancelled:
                    info = f"SEV ({info})"
                    
                ziel = dep.get("direction", "Unbekannt")[:20]
                gleis = dep.get("platform") or dep.get("plannedPlatform") or "-"
                
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
                
    except Exception as e:
        pass
        
    verbindungen.sort(key=lambda x: x['zeit'])
    return verbindungen

def verarbeite_station(item):
    name, eva_id = item
    daten = hole_station_daten(eva_id)
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

# --- NEUE FUNKTION FÜR ROUTING (BAUHOF VERBINDUNGEN) ---
def hole_routing_verbindungen(start_id, ziel_id, dateiname):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    url = "https://v5.vbb.transport.rest/journeys"
    params = {
        "from": start_id,
        "to": ziel_id,
        "results": 4,          # Die nächsten 4 Verbindungen holen
        "language": "de"
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200: return

        data = res.json()
        verbindungs_liste = []

        for journey in data.get("journeys", []):
            legs = journey.get("legs", [])
            if not legs: continue

            first_leg = legs[0]
            last_leg = legs[-1]

            def format_iso_time(iso_str):
                if not iso_str: return "--:--"
                clean_str = iso_str.split("+")[0].split("Z")[0]
                dt = datetime.strptime(clean_str[:16], "%Y-%m-%dT%H:%M")
                return dt.strftime("%H:%M")

            abfahrt = format_iso_time(first_leg.get("departure"))
            ankunft = format_iso_time(last_leg.get("arrival"))

            delay = first_leg.get("departureDelay")
            delay_str = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            linie = "Fussweg"
            if "line" in first_leg and first_leg["line"]:
                linie = first_leg["line"].get("name", "Nahverkehr")

            verbindungs_liste.append({
                "abfahrt": abfahrt,
                "ankunft": ankunft,
                "linie": linie,
                "gleis": first_leg.get("departurePlatform") or "-",
                "info": delay_str,
                "umstiege": len(legs) - 1,
                "update": jetzt.strftime("%H:%M")
            })

        with open(f"{dateiname}.json", 'w', encoding='utf-8') as f:
            json.dump(verbindungs_liste, f, ensure_ascii=False, indent=4)
        print(f"Routing-Daten für {dateiname} erfolgreich aktualisiert.")
    except Exception as e:
        print(f"Fehler beim Routing für {dateiname}: {e}")

if __name__ == "__main__":
    # 1. Bestehende Bahnhofsabfragen parallel ausführen (inkl. SEV-Fix für alle Stationen)
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())

    # 2. Neue Verbindungsabfragen vom Bauhof anhängen
    # Route A: Zerbst, Bauhof -> Zerbst, Bahnhof
    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")

    # Route B: Zerbst, Bauhof -> Magdeburg Hbf
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
    
