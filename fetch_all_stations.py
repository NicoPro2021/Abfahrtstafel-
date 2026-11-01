import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# VOLLSTÄNDIGE OFFIZIELLE DB RIS-CODES (Verspätungs- & Qualitätsgründe)
DB_CODES = {
    "1": "Nähere Informationen in Kürze",
    "2": "Polizeieinsatz",
    "3": "Feuerwehreinsatz an der Strecke",
    "4": "Kurzfristiger Personalausfall",
    "5": "Ärztliche Versorgung eines Fahrgastes",
    "6": "Unbefugtes Ziehen der Notbremse",
    "7": "Personen im Gleis",
    "8": "Notarzteinsatz an der Strecke",
    "9": "Streikauswirkungen",
    "10": "Tiere im Gleis",
    "11": "Unwetter",
    "12": "Warten auf ein verspätetes Schiff",
    "13": "Pass- und Zollkontrolle",
    "14": "Technische Störung am Bahnhof",
    "15": "Beeinträchtigung durch Vandalismus",
    "16": "Entschärfung einer Fliegerbombe",
    "17": "Beschädigung einer Brücke",
    "18": "Umgestürzter Baum im Gleis",
    "19": "Unfall an einem Bahnübergang",
    "20": "Tiere im Gleis",
    "21": "Warten auf Anschlussreisende",
    "22": "Witterungsbedingte Beeinträchtigungen",
    "23": "Feuerwehreinsatz auf Bahngelände",
    "24": "Verspätung im Ausland",
    "25": "Bereitstellung weiterer Wagen",
    "26": "Abhängen von Wagen",
    "28": "Gegenstände im Gleis",
    "29": "Ersatzverkehr mit Bus ist eingerichtet",
    "31": "Bauarbeiten",
    "32": "Verzögerung beim Ein-/Ausstieg",
    "33": "Oberleitungsstörung",
    "34": "Signalstörung",
    "35": "Streckensperrung",
    "36": "Technische Störung am Zug",
    "37": "Kurzfristiger Ausfall von. Wagen",
    "38": "Technische Störung an der Strecke",
    "39": "Anhängen von zusätzlichen Wagen",
    "40": "Stellwerksstörung / -ausfall",
    "41": "Störung an einem Bahnübergang",
    "42": "Außerplanmäßige Geschwindigkeitsbeschränkung",
    "43": "Verspätung eines vorausfahrenden Zuges",
    "44": "Warten auf einen entgegenkommenden Zug",
    "45": "Überholung durch anderen Zug",
    "46": "Warten auf freie Einfahrt",
    "47": "Verspätete Bereitstellung des Zuges",
    "48": "Verspätung aus vorheriger Fahrt",
    "55": "Technische Störung an einem anderen Zug",
    "56": "Warten auf Anschlussreisende aus Bus",
    "57": "Zusätzlicher Halt zum Ein-/Ausstieg",
    "58": "Umleitung des Zuges",
    "59": "Schnee und Eis",
    "60": "Reduzierte Geschwindigkeit wegen Sturm",
    "61": "Türstörung",
    "62": "Behobene technische Störung am Zug",
    "63": "Technische Untersuchung am Zug",
    "64": "Weichenstörung",
    "65": "Erdrutsch",
    "66": "Hochwasser",
    "67": "Behördliche Maßnahme",
    "68": "Hohes Fahrgastaufkommen",
    "70": "WLAN im Zug nicht verfügbar",
    "71": "WLAN in einzelnen Wagen nicht verfügbar",
    "72": "Info-/Entertainment nicht verfügbar",
    "73": "Mehrzweckabteil vorne",
    "74": "Mehrzweckabteil hinten",
    "75": "1. Klasse vorne",
    "76": "1. Klasse hinten",
    "77": "Ohne 1. Klasse",
    "79": "Ohne Mehrzweckabteil",
    "80": "Abweichende Wagenreihung",
    "82": "Mehrere Wagen fehlen",
    "83": "Defekt an der fahrzeuggebundenen Einstiegshilfe",
    "84": "Zug verkehrt richtig gereiht",
    "85": "Ein Wagen fehlt",
    "86": "Gesamter Zug ohne Reservierung",
    "87": "Einzelne Wagen ohne Reservierung",
    "88": "Keine Qualitätsmängel",
    "89": "Reservierungen sind wieder vorhanden",
    "90": "Kein Bordbistro / Bordrestaurant",
    "91": "Fehlende Fahrradbeförderung",
    "92": "Eingeschränkte Fahrradbeförderung",
    "93": "Behindertengerechte Einrichtung fehlt",
    "94": "Ersatzbewirtschaftung",
    "95": "Universal-WC fehlt",
    "96": "Zug ist stark ausgelastet",
    "97": "Zug ist überbesetzt",
    "98": "Sonstige Qualitätsmängel",
    "99": "Verzögerungen im Betriebsablauf"
}

# Codes, die auf Bauarbeiten oder Streckensperrungen hinweisen
BAU_SPERR_CODES = {"16", "17", "18", "29", "31", "33", "34", "35", "38", "40", "42", "58", "64", "65", "66"}
BAU_KEYWORDS = ("bauarbeit", "sperrung", "ersatzverkehr", "sev", "umleitung", "oberleitung", "stellwerk", "gleiswechsel")

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8098205", "zerbst": "8013389",
    "dessau_hbf": "8010077", "rosslau": "8010302", "rodleben": "8012777",
    "bitterfeld": "8010050", "wolfen": "8013335", "magdeburg_herrenkrug": "8013455", "bad_belzig": "8010031",
    "berlin_hbf": "8011160", "brandenburg_hbf": "8010060", "biederitz": "8010047",
    "delitzsch_unt_bf": "8010076", "dessau_sued": "8011361", "gommern": "8011673",
    "magdeburg_neustadt": "8010226", "pretzier_altm": "8012673", "wusterwitz": "8013365",
    "gueterglueck": "8010154", "wittenberge": "8010382", "berlin_hbf-tief": "8098160"
}

# Bahnhöfe mit strengem Alkoholverbot / Hausrechts-Hinweisen (wie auf echten DB-Tafeln)
ALKOHOLVERBOT_STATIONEN = {
    "8010224", "8010205", "8098205", "8011160", "8098160", "8010077", "8010050", "8010060", "8010382"
}

HEADERS = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}

# Globaler Speicher für Stationsmeldungen
GLOBAL_STATION_INFOS = {}


def extrahiere_meldungen(element):
    """Liest alle <m>-Tags (Codes, HIM-Freitexte, IBIS-Texte, Bauarbeiten) aus einem XML-Element."""
    meldungen = []
    codes = set()
    ist_bau_oder_sperrung = False

    for m in element.findall('.//m'):
        # Gelöschte Meldungen ignorieren
        if m.get('del') == '1':
            continue

        code = m.get('c')
        ext_text = (m.get('ext') or m.get('int') or "").strip()
        cat = (m.get('cat') or "").strip()

        if code:
            codes.add(str(code))
            if str(code) in BAU_SPERR_CODES:
                ist_bau_oder_sperrung = True
            text = DB_CODES.get(str(code))
            if text:
                meldungen.append(text)
            elif not ext_text:
                meldungen.append(f"Störung (Code {code})")

        if ext_text:
            # Zeilenumbrüche bereinigen
            clean_ext = " ".join(ext_text.split())
            if cat and cat.lower() not in clean_ext.lower():
                clean_ext = f"{cat}: {clean_ext}"
            meldungen.append(clean_ext)
            if any(k in clean_ext.lower() for k in BAU_KEYWORDS):
                ist_bau_oder_sperrung = True

    # Duplikate entfernen unter Beibehaltung der Reihenfolge
    unique_msgs = list(dict.fromkeys(meldungen))
    return unique_msgs, ist_bau_oder_sperrung


def baue_stations_ticker(eva_id, station_msgs, aktive_baumeldungen):
    """Erzeugt die Lauftext-Informationen wie an den echten DB-Bahnhofsanzeigen."""
    hinweise = []

    # 1. Aktuelle stationsweite Störungen / Bauarbeiten / Sperrungen
    for msg in station_msgs:
        hinweise.append(f"⚠️ {msg}")

    for b_msg in aktive_baumeldungen[:3]:
        if b_msg not in station_msgs:
            hinweise.append(f"🚧 {b_msg}")

    # 2. Offizielle DB-Bahnhofshinweise (Alkoholverbot & Hausrecht)
    if eva_id in ALKOHOLVERBOT_STATIONEN:
        hinweise.append(
            "🚭🍺 Hinweis der Deutschen Bahn: Im gesamten Bahnhofsbereich sowie auf den Bahnsteigen "
            "gilt das Hausrecht der DB InfraGO AG. Der übermäßige Verzehr von Alkohol sowie das Rauchen "
            "außerhalb gekennzeichneter Raucherbereiche sind untersagt."
        )
    else:
        hinweise.append(
            "ℹ️ Hinweis: Bitte beachten Sie das Rauchverbot auf dem gesamten Bahnhof sowie die "
            "örtlichen Regelungen zum Alkoholverbot im Bahnhofsbereich und in den Zügen des Nahverkehrs."
        )

    hinweise.append("🧳 Bitte lassen Sie Ihr Gepäck nicht unbeaufsichtigt.")
    return list(dict.fromkeys(hinweise))


def hole_daten_fuer_stunde(eva_id, datum, stunde, changes, station_ticker, tz):
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.content)
        verbindungen = []

        for s in root.findall('s'):
            trip_id = s.get('id')
            tl, dp = s.find('tl'), s.find('dp')
            if dp is None or tl is None:
                continue

            # Geheimer Betriebshalt (hi="1") überspringen
            if dp.get('hi') == '1':
                continue

            p_time_str = dp.get('pt')
            if not p_time_str:
                continue

            chg = changes.get(trip_id, {})
            e_time_str = chg.get('ct') or p_time_str

            p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
            e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)

            if e_time < datetime.now(tz) - timedelta(minutes=10):
                continue

            diff = int((e_time - p_time).total_seconds() / 60)

            # Zugnummer & Linienname sauber aufbauen
            cat = tl.get('c', '')
            num = tl.get('n', '')
            line_attr = dp.get('l', '')
            linie = f"{cat} {line_attr}".strip() if line_attr else f"{cat} {num}".strip()
            zug_nr = f"{cat} {num}".strip()

            # Geplanter vs. Geänderter Laufweg (für entfallende Halte & vorzeitiges Ende)
            ppth_list = [x for x in (dp.get('ppth') or "").split('|') if x]
            cpth_raw = chg.get('cpth')
            cpth_list = [x for x in cpth_raw.split('|') if x] if cpth_raw else ppth_list

            ziel_geplant = (dp.get('pde') or (ppth_list[-1] if ppth_list else "Unbekannt"))[:25]
            ziel_aktuell = (chg.get('cde') or (cpth_list[-1] if cpth_list else ziel_geplant))[:25]

            # Entfallende Halte durch Abgleich von ppth und cpth ermitteln
            entfallende_halte = [halt for halt in ppth_list if cpth_raw and halt not in cpth_list]
            via_halte = cpth_list[:-1][:4] if len(cpth_list) > 1 else []

            # Gleis & Gleiswechsel prüfen
            gleis_geplant = dp.get('pp') or "-"
            gleis_aktuell = chg.get('cp') or gleis_geplant
            gleiswechsel = bool(chg.get('cp') and chg.get('cp') != gleis_geplant)

            # Meldungen zusammenbauen
            alle_meldungen = list(chg.get('meldungen', []))
            ist_bau = chg.get('bauarbeiten', False)

            if gleiswechsel:
                alle_meldungen.insert(0, f"Heute von Gleis {gleis_aktuell} (statt Gleis {gleis_geplant})")
            if ziel_aktuell != ziel_geplant and chg.get('cs') != "c":
                alle_meldungen.insert(0, f"Fährt heute nur bis {ziel_aktuell}")
                ist_bau = True
            if entfallende_halte and chg.get('cs') != "c":
                alle_meldungen.append(f"Halt entfällt in: {', '.join(entfallende_halte[:4])}")
                ist_bau = True

            is_cancelled = (chg.get('cs') == "c")
            if is_cancelled and not alle_meldungen:
                alle_meldungen.append("Fahrt fällt heute aus")

            begruendung_str = " +++ ".join(dict.fromkeys(alle_meldungen))

            verbindungen.append({
                "sort_ts": e_time.timestamp(),
                "zeit": p_time.strftime("%H:%M"),
                "echte_zeit": e_time.strftime("%H:%M"),
                "linie": linie,
                "zug_nr": zug_nr,
                "ziel": ziel_aktuell,
                "ziel_geplant": ziel_geplant,
                "via": via_halte,
                "entfallende_halte": entfallende_halte,
                "gleis": gleis_aktuell,
                "gleis_geplant": gleis_geplant,
                "gleiswechsel": gleiswechsel,
                "info": "FÄLLT AUS" if is_cancelled else (f"+{diff}" if diff > 0 else "pünktlich"),
                "begruendung": begruendung_str,
                "meldungen": alle_meldungen,
                "bauarbeiten": ist_bau,
                "station_ticker": " +++ ".join(station_ticker)
            })
        return verbindungen
    except Exception as e:
        print(f"Fehler bei Stunde {stunde} für {eva_id}: {e}")
        return []


def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes = {}
    station_msgs = []
    aktive_baumeldungen = []

    try:
        c_res = requests.get(
            f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}",
            headers=HEADERS,
            timeout=10
        )
        if c_res.status_code == 200:
            root = ET.fromstring(c_res.content)

            # 1. Globale Bahnhofsmeldungen direkt unter <timetable> auslesen
            for m in root.findall('m'):
                if m.get('del') == '1':
                    continue
                ext = (m.get('ext') or m.get('int') or "").strip()
                if ext:
                    station_msgs.append(" ".join(ext.split()))

            # 2. Zugspezifische Änderungen & alle verschachtelten <m>-Tags auslesen
            for s in root.findall('s'):
                dp = s.find('dp')
                msgs, ist_bau = extrahiere_meldungen(s)

                if ist_bau:
                    for msg in msgs:
                        if any(k in msg.lower() for k in BAU_KEYWORDS) or "Bauarbeiten" in msg or "Streckensperrung" in msg:
                            aktive_baumeldungen.append(msg)

                changes[s.get('id')] = {
                    "ct": dp.get('ct') if dp is not None else None,
                    "cp": dp.get('cp') if dp is not None else None,
                    "cs": dp.get('cs') if dp is not None else None,
                    "cpth": dp.get('cpth') if dp is not None else None,
                    "cde": dp.get('cde') if dp is not None else None,
                    "meldungen": msgs,
                    "bauarbeiten": ist_bau,
                    "grund": " | ".join(msgs)
                }
    except Exception as e:
        print(f"fchg Fehler für {eva_id}: {e}")

    aktive_baumeldungen = list(dict.fromkeys(aktive_baumeldungen))
    station_ticker = baue_stations_ticker(eva_id, station_msgs, aktive_baumeldungen)

    GLOBAL_STATION_INFOS[eva_id] = {
        "eva": eva_id,
        "ticker": station_ticker,
        "bauarbeiten_aktiv": len(aktive_baumeldungen) > 0,
        "baumeldungen": aktive_baumeldungen,
        "alkoholverbot": eva_id in ALKOHOLVERBOT_STATIONEN,
        "update": jetzt.strftime("%H:%M")
    }

    datum_j = jetzt.strftime("%y%m%d")
    liste = hole_daten_fuer_stunde(eva_id, datum_j, jetzt.strftime("%H"), changes, station_ticker, tz)
    naechste = jetzt + timedelta(hours=1)
    liste += hole_daten_fuer_stunde(eva_id, naechste.strftime("%y%m%d"), naechste.strftime("%H"), changes, station_ticker, tz)

    # Duplikate (Überlappung zwischen zwei Stunden) nach Linie + Planzeit filtern
    seen = set()
    unique_liste = []
    for item in liste:
        key = (item["zeit"], item["linie"], item["ziel_geplant"])
        if key not in seen:
            seen.add(key)
            unique_liste.append(item)

    # Nach echtem Timestamp sortieren (verhindert 00:00 Uhr Mitternachts-Bug!)
    unique_liste.sort(key=lambda x: x['sort_ts'])

    for e in unique_liste:
        e.pop('sort_ts', None)
        e["update"] = jetzt.strftime("%H:%M")

    return unique_liste


def verarbeite_station(item):
    name, eva_id = item
    daten = hole_station_daten(eva_id)
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)


def erzeuge_global_info():
    """Erstellt global_info.json (inkl. Live-Wetter & Störungsübersicht) sowie station_infos.json."""
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    wetter_str = "⛅ --°C"

    # Live-Wetter für Sachsen-Anhalt (Zerbst/Magdeburg) kostenfrei via Open-Meteo holen
    try:
        w_res = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=51.96&longitude=12.08&current_weather=true",
            timeout=5
        )
        if w_res.status_code == 200:
            cw = w_res.json().get("current_weather", {})
            temp = round(cw.get("temperature", 0))
            wcode = cw.get("weathercode", 0)
            icon = "☀️" if wcode == 0 else ("⛅" if wcode in (1, 2, 3) else ("🌧️" if wcode < 70 else "❄️"))
            wetter_str = f"{icon} {temp}°C"
    except Exception:
        pass

    bau_count = sum(1 for v in GLOBAL_STATION_INFOS.values() if v.get("bauarbeiten_aktiv"))
    if bau_count > 0:
        title = f"Betriebsinformation ({bau_count} Bhf. mit Meldungen)"
        msg = (
            f"Aktuell liegen an {bau_count} überwachten Stationen Meldungen zu Bauarbeiten, "
            "Sperrungen oder Fahrplanänderungen vor. Bitte beachten Sie auch die örtlichen "
            "Hinweise zum Rauch- und Alkoholverbot an den Bahnhöfen."
        )
    else:
        title = "Regelbetrieb im Streckennetz"
        msg = (
            "Alle 23 überwachten Bahnhöfe melden regulären Betrieb. "
            "Bitte beachten Sie an den Stationen das Rauchverbot sowie die Regelungen zum Alkoholverbot."
        )

    global_data = {
        "title": title,
        "wetter": wetter_str,
        "nachricht": msg,
        "update": jetzt.strftime("%H:%M")
    }

    with open("global_info.json", "w", encoding="utf-8") as f:
        json.dump(global_data, f, ensure_ascii=False, indent=4)

    with open("station_infos.json", "w", encoding="utf-8") as f:
        json.dump(GLOBAL_STATION_INFOS, f, ensure_ascii=False, indent=4)


# --- FUNKTION FÜR ROUTING (BAUHOF VERBINDUNGEN) ---
def hole_routing_verbindungen(start_id, ziel_id, dateiname):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    url = "https://v5.vbb.transport.rest/journeys"
    params = {
        "from": start_id,
        "to": ziel_id,
        "results": 4,
        "language": "de",
        "remarks": "true"
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            return

        data = res.json()
        verbindungs_liste = []

        for journey in data.get("journeys", []):
            legs = journey.get("legs", [])
            if not legs:
                continue

            first_leg = legs[0]
            last_leg = legs[-1]

            def format_iso_time(iso_str):
                if not iso_str:
                    return "--:--"
                clean_str = iso_str.split("+")[0].split("Z")[0]
                dt = datetime.strptime(clean_str[:16], "%Y-%m-%dT%H:%M")
                return dt.strftime("%H:%M")

            abfahrt = format_iso_time(first_leg.get("departure"))
            ankunft = format_iso_time(last_leg.get("arrival"))

            delay = first_leg.get("departureDelay")
            delay_str = f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich"

            linie = "Fußweg"
            if "line" in first_leg and first_leg["line"]:
                linie = first_leg["line"].get("name", "Nahverkehr")

            # Hinweise / Bauarbeiten aus den Routing-Legs sammeln
            remarks = []
            for leg in legs:
                for rem in leg.get("remarks", []):
                    txt = rem.get("text") or rem.get("summary")
                    if txt:
                        remarks.append(" ".join(txt.split()))

            verbindungs_liste.append({
                "abfahrt": abfahrt,
                "ankunft": ankunft,
                "linie": linie,
                "gleis": first_leg.get("departurePlatform") or "-",
                "info": delay_str,
                "umstiege": len(legs) - 1,
                "hinweise": " | ".join(dict.fromkeys(remarks[:2])),
                "update": jetzt.strftime("%H:%M")
            })

        with open(f"{dateiname}.json", 'w', encoding='utf-8') as f:
            json.dump(verbindungs_liste, f, ensure_ascii=False, indent=4)
        print(f"Routing-Daten für {dateiname} erfolgreich aktualisiert.")
    except Exception as e:
        print(f"Fehler beim Routing für {dateiname}: {e}")


if __name__ == "__main__":
    # 1. Bestehende Bahnhofsabfragen parallel ausführen
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())

    # 2. Globale Info- und Stations-Dateien (Wetter, Bauarbeiten, Alkoholverbot) schreiben
    erzeuge_global_info()

    # 3. Verbindungsabfragen vom Bauhof anhängen
    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")

