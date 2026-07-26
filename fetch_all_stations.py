import requests
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
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
        # Timeout auf 30 Sekunden gegen Abbrüche
        res = requests.get(url, params=params, timeout=30)
        res.raise_for_status()
        
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
                
                # +++ NEUE LOGIK FÜR ALLE BAHNHOFSINFOS +++
                remarks = dep.get("remarks", [])
                alle_infos = []
                
                for r in remarks:
                    # Greift 'summary' oder 'text' ab, je nachdem, was die API liefert
                    meldung = r.get("summary") or r.get("text")
                    
                    if meldung and meldung not in alle_infos:
                        # Bereinigt mögliche HTML-Tags
                        meldung = meldung.replace("<br />", " ").replace("<a>", "").replace("</a>", "")
                        alle_infos.append(meldung)
                
                begruendung = " | ".join(alle_infos)
                # +++++++++++++++++++++++++++++++++++++++++
                
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
                
    except requests.exceptions.Timeout:
        print(f"Timeout-Fehler bei EVA {eva_id}: Server braucht zu lange.")
    except Exception as e:
        print(f"Netzwerkfehler bei EVA {eva_id}: {e}")
        
    verbindungen.sort(key=lambda x: x['zeit'])
    return verbindungen

def verarbeite_station(item):
    name, eva_id = item
    print(f"Rufe Daten für {name} ab...")
    daten = hole_station_daten(eva_id)
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
    # WICHTIG: Kurze Pause, um Rate-Limiting zu vermeiden
    time.sleep(2)

# --- NEUE FUNKTION FÜR ROUTING (BAUHOF VERBINDUNGEN) ---
def hole_routing_verbindungen(start_id, ziel_id, dateiname):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    url = "https://v5.vbb.transport.rest/journeys"
    params = {
        "from": start_id,
        "to": ziel_id,
        "results": 4,
        "language": "de"
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        res.raise_for_status()

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
        
    except requests.exceptions.Timeout:
        print(f"Timeout beim Routing für {dateiname}.")
    except Exception as e:
        print(f"Fehler beim Routing für {dateiname}: {e}")
    finally:
        time.sleep(2)

if __name__ == "__main__":
    print("Starte Datenabruf...")
    
    # 1. Bestehende Bahnhofsabfragen parallel ausführen
    # Max Workers auf 2, damit die DB API uns nicht blockiert
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(verarbeite_station, STATIONS.items())

    # 2. Neue Verbindungsabfragen vom Bauhof anhängen
    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
    
    print("Fertig! Alle JSON-Dateien sind auf dem neuesten Stand.")
