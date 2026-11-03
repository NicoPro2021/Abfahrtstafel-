import os
import re
import sys
import subprocess
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "curl_cffi"])
    from curl_cffi import requests as cffi_requests

import requests

# ==============================================================================
# ZUGANGSDATEN - ÜBER UMGEBUNGSSARIBELN ODER STANDARDS
# ==============================================================================
CLIENT_ID = os.environ.get("DB_CLIENT_ID", "647fddb98582bec8984c65e1256eb617")
CLIENT_SECRET = os.environ.get("DB_API_KEY", "6af72e24106f2250967364fac780bbe6")

# ==============================================================================
# WAGENREIHUNG: Verhalten
# ==============================================================================
REIHUNG_SCHAETZEN = os.environ.get("REIHUNG_SCHAETZEN", "0") == "1"
BAHN_TIMEOUT = 8
BAHN_MAX_BLOCKS = 3
BAHN_MIN_INTERVAL = 0.3

REIHUNG_CACHE_FILE = os.environ.get("REIHUNG_CACHE_FILE", ".reihung_cache.json")
CACHE_TTL_LIVE = 20 * 60
CACHE_TTL_NONE = 10 * 60
CACHE_MAX_AGE = 3 * 3600

# ==============================================================================
# UMLAUF-KONFIGURATION FÜR TRIEBZÜGE
# ==============================================================================
DOPPELTRAKTION_2X3_ZUEGE = {
    "16112", "16115", "16116", "16119", "16120", "16123",
    "16124", "16127", "16128", "16131", "16132", "16136", "16137"
}

FUENFTEILER_ZUEGE = {
    "16138", "16134", "16130", "16126", "16122", "16118",
    "16114", "16110", "3710", "3712", "3714", "3716", "3718"
}

# OFFIZIELLE DB RIS-CODES
DB_CODES = {
    "1": "Nähere Informationen in Kürze", "2": "Polizeieinsatz",
    "3": "Feuerwehreinsatz an der Strecke", "4": "Kurzfristiger Personalausfall",
    "5": "Ärztliche Versorgung eines Fahrgastes", "6": "Unbefugtes Ziehen der Notbremse",
    "7": "Personen im Gleis", "8": "Notarzteinsatz auf der Strecke",
    "9": "Streikauswirkungen", "10": "Tiere im Gleis",
    "11": "Unwetter", "12": "Warten auf ein verspätetes Schiff",
    "13": "Pass- und Zollkontrolle", "14": "Technische Störung am Bahnhof",
    "15": "Beeinträchtigung durch Vandalismus", "16": "Entschärfung einer Fliegerbombe",
    "17": "Beschädigung einer Brücke", "18": "Umgestürzter Baum im Gleis",
    "19": "Unfall an einem Bahnübergang", "20": "Tiere im Gleis",
    "21": "Warten auf Anschlussreisende", "22": "Witterungsbedingte Beeinträchtigungen",
    "23": "Feuerwehreinsatz auf Bahngelände", "24": "Verspätung im Ausland",
    "25": "Bereitstellung weiterer Wagen", "26": "Abhängen von Wagen",
    "27": "Gegenstände im Gleis", "28": "Gegenstände im Gleis",
    "29": "Ersatzverkehr mit Bus ist eingerichtet", "30": "Personalausfall im Stellwerk",
    "31": "Bauarbeiten", "32": "Verzögerung beim Ein-/Ausstieg",
    "33": "Defekte Oberleitung", "34": "Defektes Signal",
    "35": "Streckensperrung", "36": "Reparatur am Zug",
    "37": "Kurzfristiger Ausfall von Wagen", "38": "Reparatur an der Strecke",
    "39": "Anhängen von zusätzlichen Wagen", "40": "Defektes Stellwerk",
    "41": "Technischer Defekt an einem Bahnübergang", "42": "Vorübergehend verminderte Geschwindigkeit auf der Strecke",
    "43": "Verspätung eines vorausfahrenden Zuges", "44": "Warten auf einen entgegenkommenden Zug",
    "45": "Vorfahrt eines anderen Zuges", "46": "Warten auf freie Einfahrt",
    "47": "Verspätete Bereitstellung des Zuges", "48": "Verspätung aus vorheriger Fahrt",
    "49": "Kurzfristiger Personalausfall", "50": "Kurzfristige Erkrankung von Personal",
    "51": "Verspätetes Personal aus vorheriger Fahrt", "52": "Streik",
    "53": "Unwetterauswirkungen", "54": "Verfügbarkeit der Gleise derzeit eingeschränkt",
    "55": "Technischer Defekt an einem anderen Zug", "56": "Warten auf Anschlussreisende aus einem Bus",
    "57": "Zusätzlicher Halt zum Ein- und Ausstieg", "58": "Umleitung des Zuges",
    "59": "Schnee und Eis", "60": "Witterungsbedingt verminderte Geschwindigkeit",
    "61": "Defekte Tür", "63": "Technische Untersuchung am Zug",
    "64": "Weichenstörung", "65": "Erdrutsch",
    "66": "Hochwasser", "67": "Behördliche Maßnahme",
    "68": "Hohes Fahrgastaufkommen verzögert den Ein- und Ausstieg", "69": "Zug verkehrt mit verminderter Geschwindigkeit",
    "70": "WLAN nicht verfügbar", "71": "WLAN in einzelnen Wagen nicht verfügbar",
    "72": "Info-/Entertainment nicht verfügbar", "73": "Heute: Mehrzweckabteil vorne",
    "74": "Heute: Mehrzweckabteil hinten", "75": "Heute: 1. Klasse vorne",
    "76": "Heute: 1. Klasse hinten", "77": "Heute ohne 1. Klasse",
    "78": "Ersatzverkehr mit Bus ist eingerichtet", "79": "Heute ohne Mehrzweckabteil",
    "80": "Abweichende Wagenreihung", "81": "Fahrzeugtausch",
    "82": "Mehrere Wagen fehlen", "83": "Defekt an fahrzeuggebundener Einstiegshilfe",
    "85": "Ein Wagen fehlt", "86": "Keine Reservierungsanzeige",
    "87": "Einzelne Wagen ohne Reservierungsanzeige", "90": "Kein Bordbistro / Bordrestaurant",
    "91": "Fehlende Fahrradbeförderung", "92": "Eingeschränkte Fahrradbeförderung",
    "93": "Behindertengerechte Einrichtung fehlt", "94": "Ersatzbewirtschaftung",
    "95": "Universal-WC fehlt", "96": "Zug ist stark ausgelastet",
    "97": "Zug ist überbesetzt", "98": "Sonstige Qualitätsmängel",
    "99": "Verzögerungen im Betriebsablauf"
}

IGNORIERTE_CODES = {"0", "62", "84", "88", "89", "1000"}
BAU_SPERR_CODES = {"16", "17", "18", "29", "31", "33", "34", "35", "38", "40", "42", "54", "58", "64", "65", "66", "78"}
BAU_KEYWORDS = ("bauarbeit", "sperrung", "ersatzverkehr", "sev", "umleitung", "oberleitung", "stellwerk", "gleiswechsel", "weichenstörung")

STATIONS = {
    "zerbst": "8013389", "dessau_hbf": "8010077", "magdeburg_hbf": "8010224",
    "bitterfeld": "8010050", "leipzig_hbf": "8010205", "leipzig_hbf_tief": "8098205",
    "berlin_hbf": "8011160", "berlin_hbf-tief": "8098160", "brandenburg_hbf": "8010060",
    "wittenberge": "8010382", "rosslau": "8010302", "rodleben": "8012777",
    "wolfen": "8013335", "magdeburg_herrenkrug": "8013455", "bad_belzig": "8010031",
    "biederitz": "8010047", "delitzsch_unt_bf": "8010076", "dessau_sued": "8011361",
    "gommern": "8011673", "magdeburg_neustadt": "8010226", "pretzier_altm": "8012673",
    "wusterwitz": "8013365", "gueterglueck": "8010154"
}

MAIN_EVA_MAP = {"8098160": "8011160", "8098205": "8010205"}
ALKOHOLVERBOT_STATIONEN = {"8010224", "8010205", "8098205", "8011160", "8098160", "8010077", "8010050", "8010060", "8010382"}

BAUREIHEN_NAMEN = {
    "0442": "Talent 2 (BR 442)", "1442": "Talent 2 (BR 442)", "2442": "Talent 2 (BR 442)",
    "3442": "Talent 2 (BR 442)", "0842": "Talent 2 (BR 442)", "1842": "Talent 2 (BR 442)",
    "2842": "Talent 2 (BR 442)", "3842": "Talent 2 (BR 442)", "0443": "Talent 2 (BR 442)",
    "1443": "Talent 2 (BR 442)", "0445": "Twindexx / KISS (BR 445)", "0446": "Twindexx Vario (BR 446)",
    "4445": "Twindexx / KISS (BR 445)", "0462": "Desiro HC (BR 462)", "1462": "Desiro HC (BR 1462)",
    "2462": "Desiro HC (BR 2462)", "3462": "Desiro HC (BR 3462)", "4462": "Desiro HC (BR 462)",
    "0862": "Desiro HC (BR 462)", "1862": "Desiro HC (BR 1462)", "0463": "Mireo (BR 463)",
    "1463": "Mireo (BR 1463)", "0863": "Mireo (BR 463)", "0425": "BR 425", "0426": "BR 426",
    "0423": "BR 423", "0430": "BR 430", "0642": "Desiro Classic (BR 642)", "0648": "LINT 41 (BR 648)",
    "1648": "LINT 41 (BR 1648)", "0650": "RegioShuttle (BR 650)", "0401": "ICE 1 (BR 401)",
    "0402": "ICE 2 (BR 402)", "0403": "ICE 3 (BR 403)", "0406": "ICE 3 (BR 406)",
    "0407": "ICE 3 Velaro D (BR 407)", "0408": "ICE 3neo (BR 408)", "0411": "ICE T (BR 411)",
    "0415": "ICE T (BR 415)", "0412": "ICE 4 (BR 412)", "9412": "ICE 4 (BR 412)"
}

HEADERS_XML = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}
HEADERS_JSON = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/json'}

BAHN_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.bahn.de",
    "Referer": "https://www.bahn.de/buchung/fahrplan/suche",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

THREAD_LOCAL = threading.local()
CACHE_LOCK = threading.Lock()
STATS_LOCK = threading.Lock()
THROTTLE_LOCK = threading.Lock()
THROTTLE_STATE = {"last": 0.0}

GLOBAL_STATION_INFOS = {}
ZUG_FORMATION_CACHE = {}
AUFZUG_CACHE = {}
HAFAS_TIMEOUT_COUNT = 0
BAHN_STATE = {"blocks_in_row": 0, "blocked": False}
REIHUNG_STATS = {}
REIHUNG_DIAG = []


def get_thread_cffi_session():
    if not hasattr(THREAD_LOCAL, "cffi_session"):
        try:
            s = cffi_requests.Session(impersonate="chrome")
        except Exception:
            s = requests.Session()
        THREAD_LOCAL.cffi_session = s
    return THREAD_LOCAL.cffi_session


def format_linienname(cat, line_attr, num):
    cat, line_attr, num = (cat or "").strip(), (line_attr or "").strip(), (num or "").strip()
    if line_attr:
        if line_attr.upper().startswith(cat.upper()):
            rest = line_attr[len(cat):].strip()
            return f"{cat} {rest}".strip() if rest else cat
        return f"{cat} {line_attr}".strip()
    return f"{cat} {num}".strip()


def trenne_gleis_und_sektoren(gleis_str):
    if not gleis_str or gleis_str == "-":
        return "-", ""
    s = " ".join(gleis_str.strip().split())
    match = re.match(r"^(\d+[a-zA-Z]?)\s+([A-G](?:\s*[-–]\s*[A-G])?)$", s, re.IGNORECASE)
    if match:
        return match.group(1), re.sub(r"\s*[-–]\s*", "–", match.group(2).upper())
    return s, ""


def ermittle_baureihe(vehicles, grp_obj=None, fallback_desc=""):
    if isinstance(grp_obj, dict):
        br_info = grp_obj.get("baureihe")
        if isinstance(br_info, dict):
            b_name, b_num = br_info.get("name") or "", str(br_info.get("baureihe") or "").strip()
            if b_name and b_num and b_num not in b_name:
                return f"{b_name} (BR {b_num})"
            if b_name or b_num:
                return b_name or f"BR {b_num}"
        grp_digits = re.sub(r"\D", "", str(grp_obj.get("name") or ""))
        if len(grp_digits) >= 4 and grp_digits[:4] in BAUREIHEN_NAMEN:
            return BAUREIHEN_NAMEN[grp_digits[:4]]

    for v in vehicles:
        vid = re.sub(r"\D", "", str(v.get("vehicleID") or v.get("uic") or v.get("fahrzeugnummer") or ""))
        if len(vid) == 12 and vid.startswith("9") and vid[2:4] == "80":
            br_code = vid[4:8]
            if br_code in BAUREIHEN_NAMEN:
                return BAUREIHEN_NAMEN[br_code]
            if br_code.lstrip("0"):
                return f"BR {br_code.lstrip('0')}"
        v_type = v.get("type") if isinstance(v.get("type"), dict) else {}
        ct = str(v_type.get("constructionType") or "").strip()
        if ct:
            if ct.zfill(4) in BAUREIHEN_NAMEN:
                return BAUREIHEN_NAMEN[ct.zfill(4)]
            if ct.isdigit():
                return f"BR {ct}"
    if fallback_desc and fallback_desc not in ("Regional-Express", "Regionalbahn", "S-Bahn", "Zug"):
        return fallback_desc
    return ""


def _fahrzeuge_von(grp):
    return grp.get("vehicles") or grp.get("coaches") or grp.get("allFahrzeug") or []


def _pos_start(v):
    pp = v.get("platformPosition")
    if isinstance(pp, dict):
        s = pp.get("start")
        if isinstance(s, (int, float)) and not isinstance(s, bool):
            return float(s)
    return None


def sortiere_nach_bahnsteigposition(groups):
    alle = [v for g in groups for v in _fahrzeuge_von(g)]
    if not alle or any(_pos_start(v) is None for v in alle):
        return groups
    neue = []
    for g in groups:
        g2 = dict(g)
        vs = sorted(_fahrzeuge_von(g), key=_pos_start)
        for k in ("vehicles", "coaches", "allFahrzeug"):
            if g.get(k):
                g2[k] = vs
                break
        neue.append(g2)
    neue.sort(key=lambda g: _pos_start(_fahrzeuge_von(g)[0]) if _fahrzeuge_von(g) else 1e9)
    return neue


def ermittle_richtung(data, seq_obj):
    plattform = data.get("platform") if isinstance(data.get("platform"), dict) else {}
    for quelle in (data, seq_obj, plattform):
        if not isinstance(quelle, dict):
            continue
        raw = quelle.get("direction")
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.strip().isdigit()):
            wert = int(float(raw))
            if wert == 0:
                return "links"
            if wert == 100:
                return "rechts"
    return ""


def parse_wagenreihung_json(data, cat=""):
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None
    if "result" in data and isinstance(data["result"], dict):
        data = data["result"].get("data")
        if isinstance(data, dict) and "json" in data:
            data = data["json"]
    if not isinstance(data, dict):
        return None

    seq_obj = data.get("sequence") if isinstance(data.get("sequence"), dict) else data
    groups = (
        seq_obj.get("groups")
        or seq_obj.get("allFahrzeuggruppe")
        or data.get("data", {}).get("istformation", {}).get("allFahrzeuggruppe")
        or []
    )
    if not groups:
        return None

    groups = sortiere_nach_bahnsteigposition(groups)
    richtung = ermittle_richtung(data, seq_obj)

    zugteile, flache_wagen_liste, sektoren_alle, baureihen_gefunden = [], [], [], []
    up_cat = (cat or "").upper()
    ist_regio = up_cat not in ("ICE", "IC", "EC", "EN", "NJ", "FLX", "D")

    # Jedes Element in 'groups' ist exakt ein eigenständiger Zugteil
    for idx, grp in enumerate(groups):
        teil_nr = idx + 1
        bez = grp.get("transport", {}).get("description") or grp.get("zugbezeichnung") or grp.get("name") or ""
        ziel_grp = grp.get("transport", {}).get("destination", {}).get("name") or grp.get("destinationName") or ""
        vehicles = grp.get("vehicles") or grp.get("coaches") or grp.get("allFahrzeug") or []

        br_name = ermittle_baureihe(vehicles, grp, str(bez))
        if br_name and br_name not in baureihen_gefunden:
            baureihen_gefunden.append(br_name)

        gruppe_wagen = []
        for vehicle in vehicles:
            if bool(vehicle.get("closed")) or str(vehicle.get("status") or "").upper() in ("CLOSED", "GESCHLOSSEN"):
                continue
            v_type = vehicle.get("type") if isinstance(vehicle.get("type"), dict) else {}
            cat_type = str(v_type.get("category") or vehicle.get("category") or vehicle.get("kategorie") or "").upper()
            sektor = vehicle.get("platformPosition", {}).get("sector") or vehicle.get("position", {}).get("sector") or ""
            if sektor and sektor not in sektoren_alle:
                sektoren_alle.append(sektor)

            coach_cls_num = vehicle.get("class")
            features = vehicle.get("features") if isinstance(vehicle.get("features"), dict) else {}
            has_1 = bool(v_type.get("hasFirstClass") or coach_cls_num in (1, 12) or "FIRST" in cat_type)
            has_2 = bool(v_type.get("hasEconomyClass") or coach_cls_num in (2, 12) or "ECONOMY" in cat_type or "SECOND" in cat_type)
            has_bistro = bool(v_type.get("hasBistro") or coach_cls_num == 4 or features.get("dining") or "DINING" in cat_type or "BISTRO" in cat_type)

            if not has_1 and not has_2 and not has_bistro and any(k in cat_type for k in ("LOCOMOTIVE", "LOK", "POWERCAR", "TRIEBKOPF")):
                continue

            w_nr = vehicle.get("wagonIdentificationNumber") or vehicle.get("identificationNumber") or ""
            amenities = vehicle.get("amenities") or vehicle.get("ausstattung") or []
            am_types = {str(a.get("type") or a.get("art") or "").upper() for a in amenities if isinstance(a, dict)}
            hat_klima = bool(features.get("airConditioning", True)) if features else (("AIR_COND" in " ".join(am_types)) if amenities else True)
            hat_fahrrad = bool(features.get("bike") or features.get("multiPurpose")) if features else bool(
                v_type.get("hasBikeSpace") or "BIKE_SPACE" in am_types or "MULTI_PURPOSE" in am_types or "BIKE" in cat_type
            )
            hat_rollstuhl = any("WHEELCHAIR" in t or "ROLLSTUHL" in t for t in am_types)
            hat_wc = any("TOILET" in t or t == "WC" for t in am_types)

            if has_bistro and not has_1 and not has_2:
                klasse = "Bistro"
            elif coach_cls_num == 12 or (has_1 and has_2) or (has_1 and ist_regio):
                klasse = "2+1"
            elif has_1:
                klasse = "1"
            elif has_bistro:
                klasse = "Bistro"
            else:
                klasse = "2"

            w_obj = {
                "wagen": str(w_nr) if w_nr else "",
                "klasse": klasse,
                "sektor": sektor,
                "klima": hat_klima,
                "fahrrad": hat_fahrrad,
                "rollstuhl": hat_rollstuhl,
                "wc": hat_wc,
                "zugteil": teil_nr
            }
            gruppe_wagen.append(w_obj)
            flache_wagen_liste.append(w_obj)

        if gruppe_wagen:
            anz = len(gruppe_wagen)
            teil_typ = f"{anz}-Teiler" if ist_regio else f"{anz} Wagen"
            zugteile.append({
                "teil_nr": teil_nr,
                "bezeichnung": f"{teil_nr}. Zugteil ({teil_typ})" if len(groups) > 1 else teil_typ,
                "ziel": ziel_grp,
                "wagen": gruppe_wagen
            })

    if not zugteile:
        return None

    gesamt_einheiten = len(zugteile)
    laengen = [len(z["wagen"]) for z in zugteile]
    if ist_regio:
        if gesamt_einheiten > 1 and len(set(laengen)) == 1:
            formation_str = f"{gesamt_einheiten}x {laengen[0]}-Teiler ({gesamt_einheiten} Züge)"
        elif gesamt_einheiten > 1:
            formation_str = " + ".join(f"{l}-Teiler" for l in laengen) + f" ({gesamt_einheiten} Züge)"
        else:
            formation_str = f"{laengen[0]}-Teiler"
    else:
        formation_str = f"{gesamt_einheiten} Zugteile ({sum(laengen)} Wagen)" if gesamt_einheiten > 1 else f"{sum(laengen)} Wagen"

    br_str = " + ".join(baureihen_gefunden)
    zug_modell = f"{br_str} • {formation_str}" if br_str else formation_str
    sektor_str = f"{sektoren_alle[0]}–{sektoren_alle[-1]}" if len(sektoren_alle) > 1 else (sektoren_alle[0] if sektoren_alle else "")

    return {
        "modell": zug_modell,
        "formation": formation_str,
        "sektoren": sektor_str,
        "zugteile": zugteile,
        "wagen": flache_wagen_liste,
        "text": f"{zug_modell} • Sektor {sektor_str}" if sektor_str else zug_modell,
        "quelle": "live",
        "richtung": richtung
    }


def baue_konsistente_linien_reihung(cat, fahrt_nr, linie, wings, sektoren_aus_gleis, alle_meldungen):
    up_line = (linie or "").upper().strip()
    up_cat = (cat or "").upper().strip()
    nr_str = str(fahrt_nr).strip()
    nr_int = int(nr_str) if nr_str.isdigit() else 0

    ist_doppeltraktion = bool(wings or nr_str in DOPPELTRAKTION_2X3_ZUEGE)
    ist_fuenfteiler = bool(nr_str in FUENFTEILER_ZUEGE or (up_line == "RE 14" and nr_int % 2 == 0) or up_line == "RE 7")

    def baue_triebzug_einheit(anz_wagen, teil_nr, gesamt_teile):
        w_liste = []
        for i in range(anz_wagen):
            ist_letzter = (i == anz_wagen - 1)
            hat_rad = (i in (1, 2, 4)) if anz_wagen == 5 else (i in (0, 1))
            w_liste.append({
                "wagen": "",
                "klasse": "2+1" if ist_letzter else "2",
                "sektor": "",
                "klima": True,
                "fahrrad": hat_rad,
                "rollstuhl": (i == 1),
                "wc": (i == 1 or ist_letzter),
                "zugteil": teil_nr
            })
        return {
            "teil_nr": teil_nr,
            "bezeichnung": f"{teil_nr}. Zugteil ({anz_wagen}-Teiler)" if gesamt_teile > 1 else f"{anz_wagen}-Teiler",
            "ziel": "",
            "wagen": w_liste
        }

    if up_line in ("RE 13", "RE 14", "RB 50", "RB 40", "RB 113", "RE 7", "RB 33", "RB 20", "RB 22") or up_cat.startswith("S") or up_line.startswith("S "):
        modell_basis = "Talent 2 (BR 442)"
        if ist_doppeltraktion:
            zugteile = [baue_triebzug_einheit(3, 1, 2), baue_triebzug_einheit(3, 2, 2)]
            formation = "2x 3-Teiler (2 Züge)"
        elif ist_fuenfteiler:
            zugteile = [baue_triebzug_einheit(5, 1, 1)]
            formation = "5-Teiler"
        else:
            zugteile = [baue_triebzug_einheit(3, 1, 1)]
            formation = "3-Teiler"
    elif up_cat == "OE" or up_line.startswith("OE") or up_line in ("RE 1", "RE 8", "RB 10"):
        modell_basis = "ODEG Stadler KISS (BR 445)" if up_line != "RE 1" else "ODEG Desiro HC (BR 462)"
        anz = 6 if up_line == "RE 1" else 4
        formation = f"{anz}-Teiler"
        zugteile = [baue_triebzug_einheit(anz, 1, 1)]
    elif "FEX" in up_line or up_line in ("RE 3", "RE 4", "RE 5", "RE 20"):
        modell_basis = "Twindexx Vario (BR 445)"
        anz = 4 if "FEX" in up_line or up_line == "RE 20" else 5
        formation = f"{anz}-Teiler"
        zugteile = [baue_triebzug_einheit(anz, 1, 1)]
    elif up_cat in ("ICE", "IC", "EC", "FLX", "D", "EN", "NJ"):
        return None
    else:
        modell_basis = "Talent 2 (BR 442)"
        formation = "3-Teiler"
        zugteile = [baue_triebzug_einheit(3, 1, 1)]

    flache_wagen = [w for z in zugteile for w in z["wagen"]]
    voll_modell = f"~{modell_basis} • {formation}"
    return {
        "modell": voll_modell,
        "formation": formation,
        "sektoren": sektoren_aus_gleis,
        "zugteile": zugteile,
        "wagen": flache_wagen,
        "text": f"{voll_modell} • Sektor {sektoren_aus_gleis}" if sektoren_aus_gleis else voll_modell,
        "quelle": "geschaetzt"
    }


def _zaehle(name):
    with STATS_LOCK:
        REIHUNG_STATS[name] = REIHUNG_STATS.get(name, 0) + 1


def _diag(msg):
    with STATS_LOCK:
        if len(REIHUNG_DIAG) < 25:
            REIHUNG_DIAG.append(msg)
            print(f"  [Wagenreihung] {msg}")


def _drossele():
    with THROTTLE_LOCK:
        warte = BAHN_MIN_INTERVAL - (time.monotonic() - THROTTLE_STATE["last"])
        if warte > 0:
            time.sleep(warte)
        THROTTLE_STATE["last"] = time.monotonic()


def bahn_abfrage(url):
    with STATS_LOCK:
        if BAHN_STATE["blocked"]:
            return "blockiert", None, "bahn.de gesperrt"

    session = get_thread_cffi_session()
