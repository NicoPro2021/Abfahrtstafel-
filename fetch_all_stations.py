import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

# VOLLSTÄNDIGE OFFIZIELLE DB RIS-CODES (inkl. Personal-Codes 49-51 & DB-Navigator-Wortlaut)
DB_CODES = {
    "1": "Nähere Informationen in Kürze",
    "2": "Polizeieinsatz",
    "3": "Feuerwehreinsatz an der Strecke",
    "4": "Kurzfristiger Personalausfall",
    "5": "Ärztliche Versorgung eines Fahrgastes",
    "6": "Unbefugtes Ziehen der Notbremse",
    "7": "Personen im Gleis",
    "8": "Notarzteinsatz auf der Strecke",
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
    "27": "Gegenstände im Gleis",
    "28": "Gegenstände im Gleis",
    "29": "Ersatzverkehr mit Bus ist eingerichtet",
    "30": "Personalausfall im Stellwerk",
    "31": "Bauarbeiten",
    "32": "Verzögerung beim Ein-/Ausstieg",
    "33": "Defekte Oberleitung",
    "34": "Defektes Signal",
    "35": "Streckensperrung",
    "36": "Reparatur am Zug",
    "37": "Kurzfristiger Ausfall von Wagen",
    "38": "Reparatur an der Strecke",
    "39": "Anhängen von zusätzlichen Wagen",
    "40": "Defektes Stellwerk",
    "41": "Technischer Defekt an einem Bahnübergang",
    "42": "Vorübergehend verminderte Geschwindigkeit auf der Strecke",
    "43": "Verspätung eines vorausfahrenden Zuges",
    "44": "Warten auf einen entgegenkommenden Zug",
    "45": "Vorfahrt eines anderen Zuges",
    "46": "Warten auf freie Einfahrt",
    "47": "Verspätete Bereitstellung des Zuges",
    "48": "Verspätung aus vorheriger Fahrt",
    "49": "Kurzfristiger Personalausfall",
    "50": "Kurzfristige Erkrankung von Personal",
    "51": "Verspätetes Personal aus vorheriger Fahrt",
    "52": "Streik",
    "53": "Unwetterauswirkungen",
    "54": "Verfügbarkeit der Gleise derzeit eingeschränkt",
    "55": "Technischer Defekt an einem anderen Zug",
    "56": "Warten auf Anschlussreisende aus einem Bus",
    "57": "Zusätzlicher Halt zum Ein- und Ausstieg",
    "58": "Umleitung des Zuges",
    "59": "Schnee und Eis",
    "60": "Witterungsbedingt verminderte Geschwindigkeit",
    "61": "Defekte Tür",
    "63": "Technische Untersuchung am Zug",
    "64": "Weichenstörung",
    "65": "Erdrutsch",
    "66": "Hochwasser",
    "67": "Behördliche Maßnahme",
    "68": "Hohes Fahrgastaufkommen verzögert den Ein- und Ausstieg",
    "69": "Zug verkehrt mit verminderter Geschwindigkeit",
    "70": "WLAN nicht verfügbar",
    "71": "WLAN in einzelnen Wagen nicht verfügbar",
    "72": "Info-/Entertainment nicht verfügbar",
    "73": "Heute: Mehrzweckabteil vorne",
    "74": "Heute: Mehrzweckabteil hinten",
    "75": "Heute: 1. Klasse vorne",
    "76": "Heute: 1. Klasse hinten",
    "77": "Heute ohne 1. Klasse",
    "78": "Ersatzverkehr mit Bus ist eingerichtet",
    "79": "Heute ohne Mehrzweckabteil",
    "80": "Abweichende Wagenreihung",
    "81": "Fahrzeugtausch",
    "82": "Mehrere Wagen fehlen",
    "83": "Defekt an fahrzeuggebundener Einstiegshilfe",
    "85": "Ein Wagen fehlt",
    "86": "Keine Reservierungsanzeige",
    "87": "Einzelne Wagen ohne Reservierungsanzeige",
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

# Codes, die ignoriert werden (0 & 1000 sind leere Container-Codes, 62/84/88/89 sind Entwarnungen)
IGNORIERTE_CODES = {"0", "62", "84", "88", "89", "1000"}

BAU_SPERR_CODES = {"16", "17", "18", "29", "31", "33", "34", "35", "38", "40", "42", "54", "58", "64", "65", "66", "78"}
BAU_KEYWORDS = ("bauarbeit", "sperrung", "ersatzverkehr", "sev", "umleitung", "oberleitung", "stellwerk", "gleiswechsel", "weichenstörung")

STATIONS = {
    "magdeburg_hbf": "8010224", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8098205", "zerbst": "8013389",
    "dessau_hbf": "8010077", "rosslau": "8010302", "rodleben": "8012777",
    "bitterfeld": "8010050", "wolfen": "8013335", "magdeburg_herrenkrug": "8013455", "bad_belzig": "8010031",
    "berlin_hbf": "8011160", "brandenburg_hbf": "8010060", "biederitz": "8010047",
    "delitzsch_unt_bf": "8010076", "dessau_sued": "8011361", "gommern": "8011673",
    "magdeburg_neustadt": "8010226", "pretzier_altm": "8012673", "wusterwitz": "8013365",
    "gueterglueck": "8010154", "wittenberge": "8010382", "berlin_hbf-tief": "8098160"
}

# Bahnhöfe mit striktem Alkoholverbot / Hausrechts-Fokus
ALKOHOLVERBOT_STATIONEN = {
    "8010224", "8010205", "8098205", "8011160", "8098160", "8010077", "8010050", "8010060", "8010382"
}

HEADERS_XML = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}
HEADERS_JSON = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/json'}

GLOBAL_STATION_INFOS = {}
WAGENREIHUNG_CACHE = {}


def format_linienname(cat, line_attr, num):
    """Verhindert doppelte Gattungen wie 'RE RE13', 'RB RB113' oder 'S S8'."""
    cat = (cat or "").strip()
    line_attr = (line_attr or "").strip()
    num = (num or "").strip()

    if line_attr:
        up_line = line_attr.upper()
        up_cat = cat.upper()
        if up_line.startswith(up_cat):
            rest = line_attr[len(cat):].strip()
            return f"{cat} {rest}".strip() if rest else cat
        return f"{cat} {line_attr}".strip()
    return f"{cat} {num}".strip()


def hole_defekte_aufzuege(eva_id):
    """
    Prüft über die DB StaDa v2 & FaSta v2 API (falls im Account aktiviert),
    welche Aufzüge oder Rolltreppen am Bahnhof aktuell defekt (INACTIVE) sind.
    """
    defekte = []
    try:
        # 1. Bahnhofsnummer über StaDa v2 anhand der EVA-Nummer ermitteln
        st_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations?eva={eva_id}"
        st_res = requests.get(st_url, headers=HEADERS_JSON, timeout=4)
        if st_res.status_code == 200:
            res_list = st_res.json().get("result", [])
            if res_list:
                station_nr = res_list[0].get("number")
                if station_nr:
                    # 2. Anlagenstatus über FaSta v2 abrufen
                    fa_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/fasta/v2/stations/{station_nr}"
                    fa_res = requests.get(fa_url, headers=HEADERS_JSON, timeout=4)
                    if fa_res.status_code == 200:
                        for fac in fa_res.json().get("facilities", []):
                            if fac.get("state") == "INACTIVE":
                                f_type = "Aufzug" if fac.get("type") == "ELEVATOR" else "Rolltreppe"
                                desc = fac.get("description") or f"Anlage {fac.get('equipmentnumber', '')}"
                                defekte.append(f"🛗 {f_type} außer Betrieb ({desc})")
    except Exception:
        pass
    return list(dict.fromkeys(defekte))


def hole_wagenreihung(cat, fahrt_nr, eva_id, p_time_berlin):
    """
    Ruft kostenlos die Live-Wagenreihung & Bahnsteigsektoren direkt von der bahn.de Web-API ab.
    """
    if not cat or not fahrt_nr:
        return None

    cache_key = (cat, str(fahrt_nr), str(eva_id), p_time_berlin.strftime("%Y%m%d%H%M"))
    if cache_key in WAGENREIHUNG_CACHE:
        return WAGENREIHUNG_CACHE[cache_key]

    utc_time = p_time_berlin.astimezone(timezone.utc)
    date_str = p_time_berlin.strftime("%Y-%m-%d")
    iso_time = utc_time.strftime("%Y-%m-%dT%H:%M:00.000Z")

    url = "https://www.bahn.de/web/api/reisebegleitung/wagenreihung/vehicle-sequence"
    params = {
        "administrationId": "80",
        "category": cat,
        "date": date_str,
        "evaNumber": str(eva_id),
        "number": str(fahrt_nr),
        "time": iso_time
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=3.5)
        if res.status_code != 200:
            WAGENREIHUNG_CACHE[cache_key] = None
            return None

        data = res.json()
        groups = data.get("groups", [])
        if not groups:
            WAGENREIHUNG_CACHE[cache_key] = None
            return None

        wagen_liste = []
        sektoren_alle = []
        sektoren_1kl = []
        sektoren_bistro = []
        zug_modell = ""

        for grp in groups:
            bez = grp.get("transport", {}).get("description", "")
            if bez and not zug_modell:
                zug_modell = bez

            for vehicle in grp.get("vehicles", []):
                if vehicle.get("status") == "CLOSED":
                    continue
                w_nr = vehicle.get("wagonIdentificationNumber")
                sektor = vehicle.get("platformPosition", {}).get("sector", "")
                v_type = vehicle.get("type", {})
                cat_type = v_type.get("category", "")

                # Triebköpfe/Loks ohne Fahrgastbereich überspringen, außer für Sektor-Berechnung
                if sektor and sektor not in sektoren_alle:
                    sektoren_alle.append(sektor)

                if "POWERCAR" in cat_type or "LOCOMOTIVE" in cat_type:
                    continue

                ist_1kl = bool(v_type.get("hasFirstClass") or "FIRST" in cat_type)
                ist_bistro = bool(v_type.get("hasBistro") or "DINING" in cat_type or "BISTRO" in cat_type)
                ist_fahrrad = bool(v_type.get("hasBikeSpace"))

                klasse = "Bistro" if ist_bistro else ("1" if ist_1kl else "2")

                if ist_1kl and sektor and sektor not in sektoren_1kl:
                    sektoren_1kl.append(sektor)
                if ist_bistro and sektor and sektor not in sektoren_bistro:
                    sektoren_bistro.append(sektor)

                wagen_liste.append({
                    "wagen": str(w_nr) if w_nr else "",
                    "klasse": klasse,
                    "sektor": sektor,
                    "fahrrad": ist_fahrrad
                })

        sektor_str = ""
        if len(sektoren_alle) > 1:
            sektor_str = f"{sektoren_alle[0]}–{sektoren_alle[-1]}"
        elif len(sektoren_alle) == 1:
            sektor_str = sektoren_alle[0]

        info_parts = []
        if zug_modell:
            info_parts.append(zug_modell)
        if sektor_str:
            info_parts.append(f"Hält in Sektor {sektor_str}")
        if sektoren_1kl:
            info_parts.append(f"1. Kl. in {'/'.join(sektoren_1kl)}")
        if sektoren_bistro:
            info_parts.append(f"Bistro in {'/'.join(sektoren_bistro)}")

        result = {
            "modell": zug_modell,
            "sektoren": sektor_str,
            "wagen": wagen_liste,
            "text": " • ".join(info_parts)
        }
        WAGENREIHUNG_CACHE[cache_key] = result
        return result
    except Exception:
        WAGENREIHUNG_CACHE[cache_key] = None
        return None


def hole_live_hafas_meldungen(eva_id):
    """
    Ruft echte Live-Freitextmeldungen (Bauarbeiten, Sperrungen, Aufzugsstörungen, Zug-Infos)
    vom HAFAS-Server ab.
    """
    zug_freitexte = {}
    bahnhof_ticker = []
    defekte_hafas = []

    try:
        url = f"https://v5.vbb.transport.rest/stops/{eva_id}/departures"
        params = {"duration": 90, "remarks": "true", "language": "de"}
        res = requests.get(url, params=params, timeout=8)
        if res.status_code != 200:
            return zug_freitexte, bahnhof_ticker, defekte_hafas

        data = res.json()
        departures = data.get("departures", data) if isinstance(data, dict) else data

        for dep in departures:
            when_str = dep.get("plannedWhen") or dep.get("when") or ""
            zeit_key = when_str[11:16] if len(when_str) >= 16 else ""
            line_name = (dep.get("line") or {}).get("name", "").replace(" ", "").upper()

            zug_hints = []
            for rem in dep.get("remarks", []):
                r_type = rem.get("type", "")
                code = str(rem.get("code", "")).lower()
                text = (rem.get("text") or rem.get("summary") or "").strip()
                if not text:
                    continue
                clean_text = " ".join(text.split())

                if code in ("bf", "fb", "eh") or clean_text.lower() in (
                    "fahrradmitnahme begrenzt möglich",
                    "fahrzeuggebundene einstiegshilfe vorhanden",
                    "pflicht zur mund-nasen-bedeckung"
                ):
                    continue

                if any(k in clean_text.lower() for k in ("aufzug", "fahrstuhl", "rolltreppe")):
                    defekte_hafas.append(f"🛗 {clean_text}")

                if r_type in ("warning", "status") or any(k in clean_text.lower() for k in ("bauarbeit", "sperrung", "ersatzverkehr", "alkohol", "rauchverbot", "hausrecht")):
                    bahnhof_ticker.append(clean_text)

                if r_type in ("warning", "status"):
                    zug_hints.append(clean_text)

            if zeit_key and line_name and zug_hints:
                zug_freitexte[(zeit_key, line_name)] = list(dict.fromkeys(zug_hints))

    except Exception as e:
        print(f"HAFAS Live-Info Hinweis für {eva_id}: {e}")

    return zug_freitexte, list(dict.fromkeys(bahnhof_ticker)), list(dict.fromkeys(defekte_hafas))


def extrahiere_meldungen(element):
    """Liest alle gültigen <m>-Tags aus der DB-XML, ignoriert Code 0 und Code 1000."""
    meldungen = []
    ist_bau_oder_sperrung = False

    for m in element.findall('.//m'):
        if m.get('del') == '1':
            continue

        code = str(m.get('c') or "").strip()
        ext_text = (m.get('ext') or m.get('int') or "").strip()
        cat = (m.get('cat') or "").strip()

        if code and code not in IGNORIERTE_CODES:
            if code in BAU_SPERR_CODES:
                ist_bau_oder_sperrung = True
            text = DB_CODES.get(code)
            if text:
                meldungen.append(text)

        if ext_text:
            clean_ext = " ".join(ext_text.split())
            if cat and cat.lower() not in clean_ext.lower() and cat.lower() != "information":
                clean_ext = f"{cat}: {clean_ext}"
            meldungen.append(clean_ext)
            if any(k in clean_ext.lower() for k in BAU_KEYWORDS):
                ist_bau_oder_sperrung = True

    return list(dict.fromkeys(meldungen)), ist_bau_oder_sperrung


def baue_kompletten_ticker(eva_id, station_msgs, aktive_baumeldungen, defekte_anlagen):
    """
    Kombiniert Live-Störungen, Bauarbeiten und defekte Aufzüge vom Server
    mit den offiziellen DB-Bahnhofshinweisen (Alkoholverbot, Rauchverbot & Gepäck).
    """
    ticker = []

    for d in defekte_anlagen:
        ticker.append(d)

    for m in station_msgs[:4]:
        ticker.append(f"⚠️ {m}" if not m.startswith(("⚠️", "🚧", "🛗")) else m)

    for b in aktive_baumeldungen[:3]:
        if b not in station_msgs:
            ticker.append(f"🚧 {b}")

    if eva_id in ALKOHOLVERBOT_STATIONEN:
        ticker.append(
            "🚭🍺 Hinweis der Deutschen Bahn: Im gesamten Bahnhofsbereich gilt das Hausrecht der DB InfraGO AG. "
            "Der Konsum von Alkohol außerhalb der Gastronomie sowie das Rauchen außerhalb gekennzeichneter Bereiche sind untersagt."
        )
    else:
        ticker.append(
            "🚭 Hinweis: Bitte beachten Sie das Rauchverbot auf dem gesamten Bahnhof sowie die Regelungen zum Alkoholverbot in den Zügen."
        )

    ticker.append("🧳 Sicherheitshinweis: Bitte lassen Sie Ihr Gepäck nicht unbeaufsichtigt und achten Sie auf Ihre Wertgegenstände.")
    return list(dict.fromkeys(ticker))


def hole_daten_fuer_stunde(eva_id, datum, stunde, changes, zug_freitexte, station_ticker, defekte_anlagen, tz):
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    try:
        res = requests.get(url, headers=HEADERS_XML, timeout=10)
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.content)
        verbindungen = []
        jetzt = datetime.now(tz)

        for s in root.findall('s'):
            trip_id = s.get('id')
            tl, dp = s.find('tl'), s.find('dp')
            if dp is None or tl is None or dp.get('hi') == '1':
                continue

            p_time_str = dp.get('pt')
            if not p_time_str:
                continue

            chg = changes.get(trip_id, {})
            e_time_str = chg.get('ct') or p_time_str

            p_time = datetime.strptime(p_time_str, "%y%m%d%H%M").replace(tzinfo=tz)
            e_time = datetime.strptime(e_time_str, "%y%m%d%H%M").replace(tzinfo=tz)

            if e_time < jetzt - timedelta(minutes=10):
                continue

            diff = int((e_time - p_time).total_seconds() / 60)

            cat = tl.get('c', '')
            num = tl.get('n', '')
            line_attr = dp.get('l', '')
            linie = format_linienname(cat, line_attr, num)
            zug_nr = f"{cat} {num}".strip()

            ppth_list = [x for x in (dp.get('ppth') or "").split('|') if x]
            cpth_raw = chg.get('cpth')
            cpth_list = [x for x in cpth_raw.split('|') if x] if cpth_raw else ppth_list

            ziel_geplant = (dp.get('pde') or (ppth_list[-1] if ppth_list else "Unbekannt"))[:25]
            ziel_aktuell = (chg.get('cde') or (cpth_list[-1] if cpth_list else ziel_geplant))[:25]

            entfallende_halte = [halt for halt in ppth_list if cpth_raw and halt not in cpth_list]
            via_halte = cpth_list[:-1][:4] if len(cpth_list) > 1 else []

            gleis_geplant = dp.get('pp') or "-"
            gleis_aktuell = chg.get('cp') or gleis_geplant
            gleiswechsel = bool(chg.get('cp') and chg.get('cp') != gleis_geplant)

            alle_meldungen = list(chg.get('meldungen', []))
            ist_bau = chg.get('bauarbeiten', False)

            plan_hhmm = p_time.strftime("%H:%M")
            norm_line = linie.replace(" ", "").upper()
            norm_nr = zug_nr.replace(" ", "").upper()
            hafas_texte = zug_freitexte.get((plan_hhmm, norm_line)) or zug_freitexte.get((plan_hhmm, norm_nr)) or []
            for ht in hafas_texte:
                if ht not in alle_meldungen:
                    alle_meldungen.append(ht)
                    if any(k in ht.lower() for k in BAU_KEYWORDS):
                        ist_bau = True

            # Live-Wagenreihung & Bahnsteigsektoren für Züge der nächsten 65 Minuten abrufen
            reihung = None
            if (e_time - jetzt).total_seconds() <= 3900 and chg.get('cs') != "c":
                reihung = hole_wagenreihung(cat, num, eva_id, p_time)

            sektoren_str = reihung.get("sektoren", "") if reihung else ""
            zug_modell = reihung.get("modell", "") if reihung else ""
            wagen_liste = reihung.get("wagen", []) if reihung else []
            reihung_info_text = reihung.get("text", "") if reihung else ""

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
                "zeit": plan_hhmm,
                "echte_zeit": e_time.strftime("%H:%M"),
                "linie": linie,
                "zug_nr": zug_nr,
                "kategorie": cat,
                "ziel": ziel_aktuell,
                "ziel_geplant": ziel_geplant,
                "via": via_halte,
                "entfallende_halte": entfallende_halte,
                "gleis": gleis_aktuell,
                "gleis_geplant": gleis_geplant,
                "gleiswechsel": gleiswechsel,
                "sektoren": sektoren_str,
                "zug_modell": zug_modell,
                "wagenreihung": wagen_liste,
                "wagenreihung_text": reihung_info_text,
                "info": "FÄLLT AUS" if is_cancelled else (f"+{diff}" if diff > 0 else "pünktlich"),
                "begruendung": begruendung_str,
                "meldungen": list(dict.fromkeys(alle_meldungen)),
                "bauarbeiten": ist_bau,
                "defekte_aufzuege": defekte_anlagen,
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

    # 1. Live-Freitexte (HAFAS) & Aufzugsstörungen holen
    zug_freitexte, hafas_ticker, defekte_hafas = hole_live_hafas_meldungen(eva_id)
    station_msgs.extend(hafas_ticker)

    # 2. Defekte Aufzüge über DB FaSta/StaDa API prüfen
    defekte_db = hole_defekte_aufzuege(eva_id)
    alle_defekte = list(dict.fromkeys(defekte_db + defekte_hafas))

    # 3. DB Timetables v1 XML-Änderungen holen
    try:
        c_res = requests.get(
            f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}",
            headers=HEADERS_XML,
            timeout=10
        )
        if c_res.status_code == 200:
            root = ET.fromstring(c_res.content)

            for m in root.findall('m'):
                if m.get('del') == '1':
                    continue
                ext = (m.get('ext') or m.get('int') or "").strip()
                if ext:
                    station_msgs.append(" ".join(ext.split()))

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
    station_ticker = baue_kompletten_ticker(eva_id, station_msgs, aktive_baumeldungen, alle_defekte)

    GLOBAL_STATION_INFOS[eva_id] = {
        "eva": eva_id,
        "ticker": station_ticker,
        "defekte_aufzuege": alle_defekte,
        "bauarbeiten_aktiv": len(aktive_baumeldungen) > 0 or len(station_msgs) > 0,
        "baumeldungen": aktive_baumeldungen,
        "alkoholverbot": eva_id in ALKOHOLVERBOT_STATIONEN,
        "update": jetzt.strftime("%H:%M")
    }

    datum_j = jetzt.strftime("%y%m%d")
    liste = hole_daten_fuer_stunde(eva_id, datum_j, jetzt.strftime("%H"), changes, zug_freitexte, station_ticker, alle_defekte, tz)
    naechste = jetzt + timedelta(hours=1)
    liste += hole_daten_fuer_stunde(eva_id, naechste.strftime("%y%m%d"), naechste.strftime("%H"), changes, zug_freitexte, station_ticker, alle_defekte, tz)

    seen = set()
    unique_liste = []
    for item in liste:
        key = (item["zeit"], item["linie"], item["ziel_geplant"])
        if key not in seen:
            seen.add(key)
            unique_liste.append(item)

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
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    wetter_str = "⛅ --°C"

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

    aktive_stationen = [v for v in GLOBAL_STATION_INFOS.values() if v.get("bauarbeiten_aktiv")]
    bau_count = len(aktive_stationen)

    if bau_count > 0:
        title = f"Betriebsinformation ({bau_count} Bahnhöfe mit Meldungen)"
        msg = (
            f"Aktuell liegen an {bau_count} überwachten Stationen Meldungen zu Bauarbeiten, "
            "Sperrungen oder Fahrplanänderungen vor. Bitte beachten Sie auch die Hinweise zur Wagenreihung."
        )
    else:
        title = "Regelbetrieb im Streckennetz"
        msg = "Alle überwachten Bahnhöfe melden regulären Betrieb. Bitte beachten Sie das Rauch- und Alkoholverbot an den Stationen."

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

            remarks = []
            for leg in legs:
                for rem in leg.get("remarks", []):
                    if rem.get("type") in ("warning", "status"):
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
    except Exception as e:
        print(f"Fehler beim Routing für {dateiname}: {e}")


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(verarbeite_station, STATIONS.items())

    erzeuge_global_info()

    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
