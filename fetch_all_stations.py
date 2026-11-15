"""
fetch_all_stations.py – Abfahrtsdaten + Wagenreihung für die Abfahrtstafel

Reparierte Version (2026-11-21):
  * DB-API-Rate-Limit: globaler Limiter (< 60 Aufrufe/min je API) + Plan-Cache pro Stunde
    -> keine "0 Züge"-Bahnhöfe mehr durch HTTP 429
  * Bei API-Fehlern bleibt die alte JSON erhalten (kein Überschreiben mit [])
  * OPS_BLOCKED von bahn.de: Pause mit wachsender Dauer statt Dauerblockade
  * S-Bahn-Wagenreihung wird übersprungen (bahn.de liefert dafür nur 404)
  * JSON-Dateien werden atomar geschrieben (Tafel liest nie halbe Dateien)
  * Zugangsdaten nur noch aus Umgebungsvariablen bzw. .env-Datei
  * Eingebauter Loop-Modus:  python3 fetch_all_stations.py --loop
  * NEU: OpenBoards-API (Nachfolger von Timetables) als Hauptquelle,
    automatischer Rückfall auf Timetables, Testmodus: --probe <EVA>
    Umschalten: DATENQUELLE=timetables in der .env
"""
import os
import re
import sys
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
import json
from collections import deque
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

import requests

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None


# ==============================================================================
# ZUGANGSDATEN (.env neben dem Skript oder Umgebungsvariablen)
# ==============================================================================
def _lade_env_datei():
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(pfad, encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#") or "=" not in zeile:
                    continue
                k, v = zeile.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_lade_env_datei()

CLIENT_ID = os.environ.get("DB_CLIENT_ID", "647fddb98582bec8984c65e1256eb617")
CLIENT_SECRET = os.environ.get("DB_API_KEY", "6af72e24106f2250967364fac780bbe6")
if not CLIENT_ID or not CLIENT_SECRET:
    print("!! DB_CLIENT_ID / DB_API_KEY fehlen – bitte in .env neben dem Skript eintragen.")

# Cloudflare Worker als Brücke zu bahn.de
CF_WORKER_URL = os.environ.get("CF_WORKER_URL", "https://bahn-proxy.erikjordantill.workers.dev/")

BAHN_TIMEOUT = 8
BAHN_MIN_INTERVAL = 2.0
BLOCK_PAUSE_START = 120      # Sekunden Pause nach dem ersten OPS_BLOCKED
BLOCK_PAUSE_MAX = 3600       # maximal 1 Stunde

DB_API_LIMIT_PRO_MIN = 55    # Marketplace erlaubt 60/min – etwas Puffer
AUFZUG_TTL = 30 * 60         # Aufzugsdaten alle 30 min neu
LOOP_PAUSE = int(os.environ.get("LOOP_PAUSE", "60"))

# Kategorien, für die bahn.de keine Wagenreihung liefert -> Budget sparen
OHNE_WAGENREIHUNG = {"S", "BUS", "SEV", "STR", "U", "TRAM"}

REIHUNG_CACHE_FILE = os.environ.get("REIHUNG_CACHE_FILE", ".reihung_cache.json")
CACHE_TTL_LIVE = 86400 * 60
CACHE_TTL_NONE = 86400 * 60
CACHE_MAX_AGE = 86400 * 3600

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
    "Accept-Language": "de-DE,de;q=0.9",
    "Referer": "https://www.bahn.de/buchung/fahrplan/suche",
}

THREAD_LOCAL = threading.local()
CACHE_LOCK = threading.Lock()
STATS_LOCK = threading.Lock()
THROTTLE_LOCK = threading.Lock()
THROTTLE_STATE = {"last": 0.0}

GLOBAL_STATION_INFOS = {}
ZUG_FORMATION_CACHE = {}
AUFZUG_CACHE = {}            # eva -> (zeitstempel, liste)
HAFAS_TIMEOUT_COUNT = 0
# "blocked" bleibt für Kompatibilität mit deinem Loop-Skript erhalten
BAHN_STATE = {"blocks_in_row": 0, "blocked": False, "blocked_until": 0.0}
REIHUNG_STATS = {}
REIHUNG_DIAG = []


# ==============================================================================
# HILFSFUNKTIONEN: DB-API MIT RATE-LIMIT, PLAN-CACHE, ATOMARES SCHREIBEN
# ==============================================================================
class ApiFehler(Exception):
    """DB-API hat nicht sauber geantwortet -> alte JSON nicht überschreiben."""


DB_API_LOCK = threading.Lock()
DB_API_AUFRUFE = {}          # api-name -> deque(zeitstempel)
PLAN_CACHE = {}              # (eva, datum, stunde) -> xml-bytes
PLAN_LOCK = threading.Lock()

# Limits je API: (max. Aufrufe, Zeitfenster in s). OpenBoards Free-Plan: 10/s
API_LIMITS = {"open-boards": (8, 1.0)}


def _api_name(url):
    m = re.search(r"/apis/([^/]+)/", url)
    return m.group(1) if m else "sonstige"


def _warte_auf_api_limit(api):
    max_aufrufe, fenster = API_LIMITS.get(api, (DB_API_LIMIT_PRO_MIN, 60.0))
    with DB_API_LOCK:
        aufrufe = DB_API_AUFRUFE.setdefault(api, deque())
        jetzt = time.monotonic()
        while aufrufe and jetzt - aufrufe[0] > fenster:
            aufrufe.popleft()
        if len(aufrufe) >= max_aufrufe:
            warte = fenster - (jetzt - aufrufe[0]) + 0.05
            if warte > 1:
                print(f"  [DB-API] Limit {api} erreicht – warte {warte:.0f}s")
            time.sleep(warte)
            jetzt = time.monotonic()
            while aufrufe and jetzt - aufrufe[0] > fenster:
                aufrufe.popleft()
        aufrufe.append(time.monotonic())


def db_get(url, headers, timeout=10):
    """GET gegen den DB API Marketplace, bleibt unter dem Limit je API."""
    api = _api_name(url)
    _warte_auf_api_limit(api)
    try:
        res = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise ApiFehler(f"{api}: {type(e).__name__}")
    if res.status_code not in (200, 404):
        print(f"  [DB-API] HTTP {res.status_code}: {url.split('/apis/')[-1]}")
    return res


def hole_plan_xml(eva_id, datum, stunde):
    """Sollfahrplan einer Stunde – ändert sich nicht, daher einmal holen und merken."""
    key = (eva_id, datum, stunde)
    with PLAN_LOCK:
        if key in PLAN_CACHE:
            return PLAN_CACHE[key]
    url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/plan/{eva_id}/{datum}/{stunde}"
    res = db_get(url, HEADERS_XML)
    if res.status_code == 404:
        inhalt = b"<timetable/>"       # Stunde ohne Fahrten = legitim leer
    elif res.status_code != 200:
        raise ApiFehler(f"plan HTTP {res.status_code}")
    else:
        inhalt = res.content
    with PLAN_LOCK:
        PLAN_CACHE[key] = inhalt
    return inhalt


def raeume_plan_cache_auf():
    grenze = (datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(hours=2)).strftime("%y%m%d%H")
    with PLAN_LOCK:
        for key in [k for k in PLAN_CACHE if f"{k[1]}{k[2]}" < grenze]:
            del PLAN_CACHE[key]


def schreibe_json(pfad, daten, indent=4):
    tmp = f"{pfad}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, pfad)


def get_thread_cffi_session():
    if not hasattr(THREAD_LOCAL, "cffi_session"):
        s = None
        if cffi_requests is not None:
            try:
                s = cffi_requests.Session(impersonate="chrome")
            except Exception:
                s = None
        THREAD_LOCAL.cffi_session = s or requests.Session()
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


# ==============================================================================
# WAGENREIHUNG – PARSER (unverändert)
# ==============================================================================
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
    if data.get("status") == "ERROR" or data.get("code") == "OPS_BLOCKED" or data.get("error"):
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

    for idx, grp in enumerate(groups):
        teil_nr = idx + 1
        bez = grp.get("transport", {}).get("description") or grp.get("zugbezeichnung") or grp.get("name") or ""
        ziel_grp = grp.get("transport", {}).get("destination", {}).get("name") or grp.get("destinationName") or ""
        vehicles = _fahrzeuge_von(grp)

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


def _zaehle(name):
    with STATS_LOCK:
        REIHUNG_STATS[name] = REIHUNG_STATS.get(name, 0) + 1


def _diag(msg):
    with STATS_LOCK:
        if len(REIHUNG_DIAG) < 15:
            REIHUNG_DIAG.append(msg)
            print(f"  [Wagenreihung] {msg}")


def _drossele():
    with THROTTLE_LOCK:
        warte = BAHN_MIN_INTERVAL - (time.monotonic() - THROTTLE_STATE["last"])
        if warte > 0:
            time.sleep(warte)
        THROTTLE_STATE["last"] = time.monotonic()


# ==============================================================================
# WAGENREIHUNG – ABFRAGE ÜBER BAHN.DE
# ==============================================================================
def _cf_worker_bridge(bahn_url):
    """Standard-Brücke: ruft bahn.de über deinen Cloudflare Worker ab (?url=...).
    Dein Loop-Skript kann BRIDGE_FUNC weiterhin selbst setzen – dann wird das hier nicht benutzt."""
    if not CF_WORKER_URL:
        return 0, ""
    try:
        r = get_thread_cffi_session().get(
            CF_WORKER_URL, params={"url": bahn_url}, headers=BAHN_HEADERS, timeout=BAHN_TIMEOUT
        )
        return r.status_code, r.text
    except Exception as e:
        return 0, f"{type(e).__name__}"


BRIDGE_FUNC = None
PERMANENT_TRAIN_CACHE = {}
NO_REIHUNG_CACHE = set()
LIVE_BUDGET_PER_ROUND = 6
LIVE_QUERIES_THIS_ROUND = 0
BUDGET_HIT_IN_STATION = False

CACHE_DAY = ""


def _extrahier_zug_key(bahn_url):
    """Erkennt Zugnummer + Datum + Bahnhof aus der bahn.de URL."""
    heute = datetime.now().strftime("%Y-%m-%d")
    m_num = re.search(r"[?&](?:zugnummer|trainNumber|number)=(\d+)", bahn_url)
    m_date = re.search(r"[?&](?:date|time|departure)=([0-9]{4}-[0-9]{2}-[0-9]{2})", bahn_url)
    m_eva = re.search(r"[?&]evaNumber=(\d+)", bahn_url)
    if m_num:
        d_str = m_date.group(1) if m_date else heute
        eva = m_eva.group(1) if m_eva else ""
        # Bahnhof gehört in den Schlüssel: Sektoren/Richtung sind je Bahnhof verschieden
        return f"ZUG_{m_num.group(1)}_{d_str}_{eva}"
    return f"{bahn_url}_{heute}"


def bahn_ist_blockiert():
    with STATS_LOCK:
        if time.time() < BAHN_STATE["blocked_until"]:
            BAHN_STATE["blocked"] = True
            return True
        BAHN_STATE["blocked"] = False
        return False


def bahn_abfrage(bahn_url):
    global LIVE_QUERIES_THIS_ROUND, BUDGET_HIT_IN_STATION, CACHE_DAY

    heute = datetime.now().strftime("%Y-%m-%d")
    with CACHE_LOCK:
        if CACHE_DAY != heute:
            PERMANENT_TRAIN_CACHE.clear()
            NO_REIHUNG_CACHE.clear()
            CACHE_DAY = heute

    train_key = _extrahier_zug_key(bahn_url)

    # 1. Schon bekannt? -> aus dem Speicher, keine Anfrage an bahn.de
    with CACHE_LOCK:
        if train_key in PERMANENT_TRAIN_CACHE:
            _zaehle("aus_filter_wiederverwendet")
            return "ok", PERMANENT_TRAIN_CACHE[train_key], ""
        if train_key in NO_REIHUNG_CACHE:
            _zaehle("bekannt_ohne_reihung")
            return "keine_daten", None, "Bereits geprüft (hat keine Reihung)"

    # 2. Pause nach OPS_BLOCKED?
    if bahn_ist_blockiert():
        BUDGET_HIT_IN_STATION = True
        rest = int(BAHN_STATE["blocked_until"] - time.time())
        return "blockiert", None, f"Pause nach OPS_BLOCKED (noch {rest // 60}:{rest % 60:02d} min)"

    # 3. Kontingent pro Runde
    with STATS_LOCK:
        if LIVE_QUERIES_THIS_ROUND >= LIVE_BUDGET_PER_ROUND:
            BUDGET_HIT_IN_STATION = True
            REIHUNG_STATS["neue_zuege_warten"] = REIHUNG_STATS.get("neue_zuege_warten", 0) + 1
            return "kontingent_voll", None, "Wartet auf nächste Runde"
        LIVE_QUERIES_THIS_ROUND += 1

    bridge = BRIDGE_FUNC or _cf_worker_bridge
    _drossele()
    status_code, body = bridge(bahn_url)
    body = (body or "").lstrip()

    if "OPS_BLOCKED" in body or status_code in (401, 403, 429):
        with STATS_LOCK:
            BAHN_STATE["blocks_in_row"] += 1
            pause = min(BLOCK_PAUSE_START * 2 ** (BAHN_STATE["blocks_in_row"] - 1), BLOCK_PAUSE_MAX)
            BAHN_STATE["blocked_until"] = time.time() + pause
            BAHN_STATE["blocked"] = True
            BUDGET_HIT_IN_STATION = True
        print(f"  [bahn.de] OPS_BLOCKED ({BAHN_STATE['blocks_in_row']}x in Folge) – Pause {pause // 60} min")
        return "blockiert", None, f"HTTP {status_code} (OPS_BLOCKED)"

    if status_code == 200 and body[:1] in ("{", "["):
        try:
            data = json.loads(body)
        except Exception:
            return "fehler", None, "JSON ungültig"
        with STATS_LOCK:
            BAHN_STATE["blocks_in_row"] = 0
        with CACHE_LOCK:
            PERMANENT_TRAIN_CACHE[train_key] = data
        return "ok", data, ""

    if status_code in (204, 404):
        with CACHE_LOCK:
            NO_REIHUNG_CACHE.add(train_key)
        return "keine_daten", None, f"HTTP {status_code}"

    return "fehler", None, f"HTTP {status_code} {body[:60]}"


def hole_wagenreihung(cat, fahrt_nr, linie, eva_id, p_time_berlin, sektoren_aus_gleis):
    if not fahrt_nr:
        return None, ""

    lookup_eva = MAIN_EVA_MAP.get(str(eva_id), str(eva_id))
    primary_cat = (cat or (linie.split()[0] if linie else "RE")).upper()
    if primary_cat == "OE" and linie:
        first_w = linie.split()[0].upper()
        if first_w in ("RE", "RB"):
            primary_cat = first_w

    if primary_cat in OHNE_WAGENREIHUNG:
        return None, ""

    utc_time = p_time_berlin.astimezone(timezone.utc)
    iso_time = utc_time.strftime("%Y-%m-%dT%H:%M:00.000Z")
    date_str = utc_time.strftime("%Y-%m-%d")

    url = (
        "https://www.bahn.de/web/api/reisebegleitung/wagenreihung/vehicle-sequence"
        f"?administrationId=80"
        f"&category={urllib.parse.quote(str(primary_cat))}"
        f"&date={date_str}"
        f"&evaNumber={lookup_eva}"
        f"&number={urllib.parse.quote(str(fahrt_nr))}"
        f"&time={iso_time}"
    )

    cache_key = f"{primary_cat}|{fahrt_nr}|{iso_time}|{lookup_eva}"
    jetzt_ts = time.time()
    with CACHE_LOCK:
        eintrag = ZUG_FORMATION_CACHE.get(cache_key)

    if eintrag and jetzt_ts - eintrag.get("t", 0) < (CACHE_TTL_LIVE if eintrag.get("data") else CACHE_TTL_NONE):
        if eintrag.get("data"):
            _zaehle("cache")
            return eintrag["data"], url
        _zaehle("keine_daten")
        return None, url

    status, data, detail = bahn_abfrage(url)
    if status == "ok":
        parsed = parse_wagenreihung_json(data, primary_cat)
        if parsed:
            if not parsed["sektoren"] and sektoren_aus_gleis:
                parsed["sektoren"] = sektoren_aus_gleis
            with CACHE_LOCK:
                ZUG_FORMATION_CACHE[cache_key] = {"t": jetzt_ts, "data": parsed}
            _zaehle("live")
            print(f"  -> [Live-Wagenreihung OK] {linie} ({fahrt_nr}) @ {lookup_eva}: {parsed['modell']}")
            return parsed, url
        status, detail = "keine_daten", "Leere Gruppen"

    if status == "keine_daten":
        with CACHE_LOCK:
            ZUG_FORMATION_CACHE[cache_key] = {"t": jetzt_ts, "data": None}

    _zaehle(status)
    if status != "blockiert" or "HTTP" in detail:   # Folge-Blockaden nicht 15x loggen
        _diag(f"{linie or primary_cat} ({fahrt_nr}) @ {lookup_eva}: {status} [{detail}]")
    return None, url


def lade_reihung_cache():
    try:
        with open(REIHUNG_CACHE_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        jetzt = time.time()
        with CACHE_LOCK:
            for k, v in raw.items():
                if isinstance(v, dict) and jetzt - v.get("t", 0) < CACHE_MAX_AGE:
                    ZUG_FORMATION_CACHE[k] = v
    except Exception:
        pass


def speichere_reihung_cache():
    jetzt = time.time()
    try:
        with CACHE_LOCK:
            frisch = {k: v for k, v in ZUG_FORMATION_CACHE.items() if jetzt - v.get("t", 0) < CACHE_MAX_AGE}
        schreibe_json(REIHUNG_CACHE_FILE, frisch, indent=None)
    except Exception:
        pass


# ==============================================================================
# STÖRUNGEN / MELDUNGEN
# ==============================================================================
def hole_defekte_aufzuege(eva_id):
    lookup_eva = MAIN_EVA_MAP.get(str(eva_id), str(eva_id))
    eintrag = AUFZUG_CACHE.get(lookup_eva)
    if eintrag and time.time() - eintrag[0] < AUFZUG_TTL:
        return eintrag[1]
    defekte = []
    try:
        st_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations?eva={lookup_eva}"
        st_res = db_get(st_url, HEADERS_JSON, timeout=3.5)
        if st_res.status_code == 200:
            res_list = st_res.json().get("result", [])
            if res_list and res_list[0].get("number"):
                fa_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/fasta/v2/stations/{res_list[0]['number']}"
                fa_res = db_get(fa_url, HEADERS_JSON, timeout=3.5)
                if fa_res.status_code == 200:
                    for fac in fa_res.json().get("facilities", []):
                        if fac.get("state") == "INACTIVE":
                            f_type = "Aufzug" if fac.get("type") == "ELEVATOR" else "Rolltreppe"
                            desc = fac.get("description") or f"Anlage {fac.get('equipmentnumber', '')}"
                            defekte.append(f"🛗 {f_type} außer Betrieb ({desc})")
    except Exception:
        if eintrag:                      # bei Fehler alten Stand weiterverwenden
            return eintrag[1]
    res_unique = list(dict.fromkeys(defekte))
    AUFZUG_CACHE[lookup_eva] = (time.time(), res_unique)
    return res_unique


def hole_live_hafas_meldungen(eva_id):
    global HAFAS_TIMEOUT_COUNT
    zug_freitexte, bahnhof_ticker, defekte_hafas = {}, [], []
    if HAFAS_TIMEOUT_COUNT >= 2:
        return zug_freitexte, bahnhof_ticker, defekte_hafas
    try:
        url = f"https://v6.db.transport.rest/stops/{eva_id}/departures"
        res = requests.get(url, params={"duration": 90, "remarks": "true", "language": "de"}, timeout=2.5)
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
    except Exception:
        HAFAS_TIMEOUT_COUNT += 1
    return zug_freitexte, list(dict.fromkeys(bahnhof_ticker)), list(dict.fromkeys(defekte_hafas))


def extrahiere_meldungen(element):
    meldungen, ist_bau = [], False
    for m in element.findall('.//m'):
        if m.get('del') == '1':
            continue
        code = str(m.get('c') or "").strip()
        ext_text = (m.get('ext') or m.get('int') or "").strip()
        cat = (m.get('cat') or "").strip()
        if code and code not in IGNORIERTE_CODES:
            if code in BAU_SPERR_CODES:
                ist_bau = True
            if code in DB_CODES:
                meldungen.append(DB_CODES[code])
        if ext_text:
            clean_ext = " ".join(ext_text.split())
            if cat and cat.lower() not in clean_ext.lower() and cat.lower() != "information":
                clean_ext = f"{cat}: {clean_ext}"
            meldungen.append(clean_ext)
            if any(k in clean_ext.lower() for k in BAU_KEYWORDS):
                ist_bau = True
    return list(dict.fromkeys(meldungen)), ist_bau


def baue_kompletten_ticker(eva_id, station_msgs, aktive_baumeldungen, defekte_anlagen):
    ticker = list(defekte_anlagen)
    for m in station_msgs[:4]:
        ticker.append(f"⚠️ {m}" if not m.startswith(("⚠️", "🚧", "🛗")) else m)
    for b in aktive_baumeldungen[:3]:
        if b not in station_msgs:
            ticker.append(f"🚧 {b}")
    if eva_id in ALKOHOLVERBOT_STATIONEN:
        ticker.append("🚭🍺 Hinweis der Deutschen Bahn: Im gesamten Bahnhofsbereich gilt das Hausrecht der DB InfraGO AG. Der Konsum von Alkohol außerhalb der Gastronomie sowie das Rauchen außerhalb gekennzeichneter Bereiche sind untersagt.")
    else:
        ticker.append("🚭 Hinweis: Bitte beachten Sie das Rauchverbot auf dem gesamten Bahnhof sowie die Regelungen zum Alkoholverbot in den Zügen.")
    ticker.append("🧳 Sicherheitshinweis: Bitte lassen Sie Ihr Gepäck nicht unbeaufsichtigt und achten Sie auf Ihre Wertgegenstände.")
    return list(dict.fromkeys(ticker))


# ==============================================================================
# ABFAHRTEN
# ==============================================================================
def hole_daten_fuer_stunde(eva_id, datum, stunde, changes, zug_freitexte, station_ticker, defekte_anlagen, tz):
    # ApiFehler fliegt hier bewusst nach oben -> alte JSON bleibt stehen
    xml_inhalt = hole_plan_xml(eva_id, datum, stunde)
    try:
        root = ET.fromstring(xml_inhalt)
    except ET.ParseError as e:
        raise ApiFehler(f"plan XML defekt: {e}")

    verbindungen = []
    jetzt = datetime.now(tz)

    for s in root.findall('s'):
        try:
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
            cat, num, line_attr = tl.get('c', ''), tl.get('n', ''), dp.get('l', '')
            linie = format_linienname(cat, line_attr, num)
            zug_nr = f"{cat} {num}".strip()

            ppth_list = [x for x in (dp.get('ppth') or "").split('|') if x]
            cpth_raw = chg.get('cpth')
            cpth_list = [x for x in cpth_raw.split('|') if x] if cpth_raw else ppth_list

            ziel_geplant = (dp.get('pde') or (ppth_list[-1] if ppth_list else "Unbekannt"))[:25]
            ziel_aktuell = (chg.get('cde') or (cpth_list[-1] if cpth_list else ziel_geplant))[:25]
            entfallende_halte = [halt for halt in ppth_list if cpth_raw and halt not in cpth_list]
            via_halte = cpth_list[:-1][:4] if len(cpth_list) > 1 else []

            raw_pp = dp.get('pp') or "-"
            raw_cp = chg.get('cp') or raw_pp
            gleis_geplant, sek_geplant = trenne_gleis_und_sektoren(raw_pp)
            gleis_aktuell, sek_aktuell = trenne_gleis_und_sektoren(raw_cp)
            sektoren_aus_gleis = sek_aktuell or sek_geplant
            gleiswechsel = bool(chg.get('cp') and gleis_aktuell != gleis_geplant)

            alle_meldungen = list(chg.get('meldungen', []))
            ist_bau = chg.get('bauarbeiten', False)

            plan_hhmm = p_time.strftime("%H:%M")
            hafas_texte = zug_freitexte.get((plan_hhmm, linie.replace(" ", "").upper())) or zug_freitexte.get((plan_hhmm, zug_nr.replace(" ", "").upper())) or []
            for ht in hafas_texte:
                if ht not in alle_meldungen:
                    alle_meldungen.append(ht)
                    if any(k in ht.lower() for k in BAU_KEYWORDS):
                        ist_bau = True

            is_cancelled = (chg.get('cs') == "c")
            reihung, reihung_url = (None, "")
            if not is_cancelled:
                reihung, reihung_url = hole_wagenreihung(cat, num, linie, eva_id, p_time, sektoren_aus_gleis)

            if gleiswechsel:
                alle_meldungen.insert(0, f"Heute von Gleis {gleis_aktuell} (statt Gleis {gleis_geplant})")
            if ziel_aktuell != ziel_geplant and not is_cancelled:
                alle_meldungen.insert(0, f"Fährt heute nur bis {ziel_aktuell}")
                ist_bau = True
            if entfallende_halte and not is_cancelled:
                alle_meldungen.append(f"Halt entfällt in: {', '.join(entfallende_halte[:4])}")
                ist_bau = True
            if is_cancelled and not alle_meldungen:
                alle_meldungen.append("Fahrt fällt heute aus")

            verbindungen.append({
                "sort_ts": e_time.timestamp(),
                "zeit": plan_hhmm,
                "echte_zeit": e_time.strftime("%H:%M"),
                "linie": linie,
                "zug_nr": zug_nr,
                "fahrt_nr": str(num),
                "kategorie": cat,
                "ziel": ziel_aktuell,
                "ziel_geplant": ziel_geplant,
                "via": via_halte,
                "entfallende_halte": entfallende_halte,
                "gleis": gleis_aktuell,
                "gleis_geplant": gleis_geplant,
                "gleiswechsel": gleiswechsel,
                "sektoren": (reihung.get("sektoren") if reihung else "") or sektoren_aus_gleis,
                "zug_modell": reihung.get("modell", "") if reihung else "",
                "formation": reihung.get("formation", "") if reihung else "",
                "zugteile": reihung.get("zugteile", []) if reihung else [],
                "wagenreihung": reihung.get("wagen", []) if reihung else [],
                "wagenreihung_text": reihung.get("text", "") if reihung else "Keine Wagenreihung verfügbar",
                "reihung_quelle": "live" if reihung else "keine",
                "reihung_richtung": reihung.get("richtung", "") if reihung else "",
                "reihung_url": reihung_url,
                "info": "FÄLLT AUS" if is_cancelled else (f"+{diff}" if diff > 0 else "pünktlich"),
                "begruendung": " +++ ".join(dict.fromkeys(alle_meldungen)),
                "meldungen": list(dict.fromkeys(alle_meldungen)),
                "bauarbeiten": ist_bau,
                "defekte_aufzuege": defekte_anlagen,
                "station_ticker": " +++ ".join(station_ticker)
            })
        except Exception as e:
            # Ein kaputter Zug soll nicht die ganze Stunde wegwerfen
            print(f"  Zug übersprungen @ {eva_id} ({stunde} Uhr): {type(e).__name__}: {e}")
    return verbindungen


def hole_station_daten(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    changes, station_msgs, aktive_baumeldungen = {}, [], []

    zug_freitexte, hafas_ticker, defekte_hafas = hole_live_hafas_meldungen(eva_id)
    station_msgs.extend(hafas_ticker)
    alle_defekte = list(dict.fromkeys(hole_defekte_aufzuege(eva_id) + defekte_hafas))

    c_res = db_get(f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}", HEADERS_XML)
    if c_res.status_code != 200:
        raise ApiFehler(f"fchg HTTP {c_res.status_code}")
    try:
        root = ET.fromstring(c_res.content)
    except ET.ParseError as e:
        raise ApiFehler(f"fchg XML defekt: {e}")

    for m in root.findall('m'):
        if m.get('del') != '1':
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
            "wings": dp.get('wings') if dp is not None else None,
            "meldungen": msgs,
            "bauarbeiten": ist_bau,
            "grund": " | ".join(msgs)
        }

    aktive_baumeldungen = list(dict.fromkeys(aktive_baumeldungen))
    station_ticker = baue_kompletten_ticker(eva_id, station_msgs, aktive_baumeldungen, alle_defekte)

    datum_j = jetzt.strftime("%y%m%d")
    liste = hole_daten_fuer_stunde(eva_id, datum_j, jetzt.strftime("%H"), changes, zug_freitexte, station_ticker, alle_defekte, tz)
    naechste = jetzt + timedelta(hours=1)
    liste += hole_daten_fuer_stunde(eva_id, naechste.strftime("%y%m%d"), naechste.strftime("%H"), changes, zug_freitexte, station_ticker, alle_defekte, tz)

    GLOBAL_STATION_INFOS[eva_id] = {
        "eva": eva_id,
        "ticker": station_ticker,
        "defekte_aufzuege": alle_defekte,
        "bauarbeiten_aktiv": len(aktive_baumeldungen) > 0 or len(station_msgs) > 0,
        "baumeldungen": aktive_baumeldungen,
        "alkoholverbot": eva_id in ALKOHOLVERBOT_STATIONEN,
        "update": jetzt.strftime("%H:%M")
    }

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


# ==============================================================================
# OPENBOARDS (Nachfolger der Timetables-API, seit Nov. 2026)
# Doku: https://developer-docs.deutschebahn.com/doku/apis/Open-API-Baustein-OpenBoards-14071662
# Benötigt ein Abo "OpenBoards" für deine Anwendung im DB API Marketplace.
# Quellenangabe laut DB: "Deutsche Bahn (OpenBoards)" – nicht CC BY 4.0.
# ==============================================================================
DATENQUELLE = os.environ.get("DATENQUELLE", "openboards").lower()   # openboards | timetables
OB_URL = "https://apis.deutschebahn.com/db-api-marketplace/apis/open-boards/v1/departures"
OB_FENSTER = int(os.environ.get("OB_FENSTER", "4"))     # Anzahl 30-min-Fenster (4 = 2 Std.)
OB_STATE = {"aus": False, "grund": "", "format_warnung": False}


class OpenBoardsFehler(ApiFehler):
    def __init__(self, msg, status=0):
        super().__init__(msg)
        self.status = status


def ob_post(body):
    _warte_auf_api_limit("open-boards")
    headers = {**HEADERS_JSON, "Content-Type": "application/json"}
    try:
        res = requests.post(OB_URL, headers=headers, json=body, timeout=10)
    except requests.RequestException as e:
        raise OpenBoardsFehler(f"OpenBoards: {type(e).__name__}")
    if res.status_code != 200:
        raise OpenBoardsFehler(f"OpenBoards HTTP {res.status_code}: {res.text[:120]}", res.status_code)
    try:
        return res.json()
    except ValueError:
        raise OpenBoardsFehler("OpenBoards: keine gültige JSON-Antwort")


def ob_anfrage(eva_id, start):
    return {
        "stopPlaceOrStation": {"evaNumbers": [str(eva_id)]},
        "timeWindow": {"timeStart": start.isoformat(timespec="seconds")},
        "maxViaStops": 4,
        "maxEntriesPerTransportType": 25,
        "languages": ["deu"],
    }


def _g(d, *pfade):
    """Erster vorhandener Wert aus mehreren möglichen Feldnamen ('a.b.c')."""
    for pfad in pfade:
        cur = d
        for teil in pfad.split("."):
            if isinstance(cur, dict) and teil in cur:
                cur = cur[teil]
            else:
                cur = None
                break
        if cur not in (None, "", [], {}):
            return cur
    return None


def _ob_eintraege(antwort):
    if isinstance(antwort, list):
        return antwort
    if isinstance(antwort, dict):
        for k in ("departures", "entries", "journeys", "items", "board"):
            if isinstance(antwort.get(k), list):
                return antwort[k]
    return []


def _ob_zeit(wert, tz):
    if not wert:
        return None
    try:
        return datetime.fromisoformat(str(wert).replace("Z", "+00:00")).astimezone(tz)
    except ValueError:
        return None


def _ob_texte(liste):
    texte = []
    for m in liste or []:
        if isinstance(m, str):
            texte.append(m)
            continue
        if not isinstance(m, dict):
            continue
        typ = str(m.get("type") or m.get("category") or "").upper()
        if "ATTRIBUTE" in typ or "FEATURE" in typ:
            continue        # Ausstattungs-Hinweise (Fahrrad etc.) nicht als Störung zeigen
        code = str(m.get("code") or "").strip()
        txt = _g(m, "text", "textLong", "textShort", "shortText", "value", "content", "message")
        if isinstance(txt, dict):
            txt = _g(txt, "deu", "de", "text")
        if isinstance(txt, list):
            txt = " ".join(str(t.get("text") if isinstance(t, dict) else t) for t in txt)
        if txt:
            texte.append(" ".join(str(txt).split()))
        elif code in DB_CODES and code not in IGNORIERTE_CODES:
            texte.append(DB_CODES[code])
    return list(dict.fromkeys(texte))


def _ob_name(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return _g(x, "name", "text", "stopPlace.name", "station.name") or ""
    return ""


def hole_station_daten_openboards(eva_id):
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)

    zug_freitexte, hafas_ticker, defekte_hafas = hole_live_hafas_meldungen(eva_id)
    alle_defekte = list(dict.fromkeys(hole_defekte_aufzuege(eva_id) + defekte_hafas))

    roh = []
    start = jetzt - timedelta(minutes=5)       # verspätete Züge mitnehmen
    for i in range(OB_FENSTER):
        try:
            roh += _ob_eintraege(ob_post(ob_anfrage(eva_id, start + timedelta(minutes=30 * i))))
        except OpenBoardsFehler:
            if i == 0:
                raise
            break                               # spätere Fenster: Liste ist dann nur kürzer

    station_msgs = list(hafas_ticker)
    aktive_baumeldungen = []
    verbindungen, gesehen = [], set()

    for e in roh:
        if not isinstance(e, dict):
            continue
        try:
            p_time = _ob_zeit(_g(e, "timeSchedule", "departure.timeSchedule", "plannedTime", "scheduledTime"), tz)
            if p_time is None:
                continue
            e_time = _ob_zeit(_g(e, "time", "departure.time", "timePredicted", "actualTime"), tz) or p_time
            if e_time < jetzt - timedelta(minutes=10):
                continue
            time_type = str(_g(e, "timeType", "departure.timeType") or "").upper()
            is_cancelled = bool(_g(e, "canceled", "cancelled", "departure.canceled", "isCanceled")) \
                or time_type in ("CANCELED", "CANCELLED")

            tr = _g(e, "transport", "journey.transport") or {}
            ersatz = bool(_g(tr, "replacementTransport") or _g(e, "replacementTransport"))
            cat = str(_g(tr, "category", "productCategory", "type") or "")
            if cat.isupper() and "_" in cat:       # z.B. REGIONAL_TRAIN -> keine Kurzform
                cat = ""
            num = str(_g(tr, "number", "journeyNumber", "trainNumber") or "")
            line = str(_g(tr, "line", "lineName", "label", "name") or "")
            linie = "SEV " + (line or cat) if ersatz else format_linienname(cat, line, num)
            zug_nr = f"{cat} {num}".strip()

            ziel_aktuell = _ob_name(_g(tr, "destination", "direction") or _g(e, "destination", "direction")) or "Unbekannt"
            ziel_geplant = _ob_name(_g(tr, "destinationSchedule", "plannedDestination")) or ziel_aktuell
            via_roh = _g(e, "viaStops", "via", "stopPlaces") or _g(tr, "via", "viaStops") or []
            via_halte = [n for n in (_ob_name(v) for v in via_roh) if n][:4] if isinstance(via_roh, list) else []
            entfallende_halte = [_ob_name(v) for v in via_roh if isinstance(v, dict)
                                 and (v.get("canceled") or v.get("cancelled"))] if isinstance(via_roh, list) else []

            gleis_geplant, sek_geplant = trenne_gleis_und_sektoren(str(_g(e, "platformSchedule", "departure.platformSchedule") or "-"))
            gleis_aktuell, sek_aktuell = trenne_gleis_und_sektoren(str(_g(e, "platform", "departure.platform") or gleis_geplant))
            sektoren_aus_gleis = sek_aktuell or sek_geplant
            gleiswechsel = gleis_aktuell != gleis_geplant and gleis_geplant != "-"

            alle_meldungen = _ob_texte(e.get("messages")) + _ob_texte(e.get("disruptions"))
            plan_hhmm = p_time.strftime("%H:%M")
            for ht in zug_freitexte.get((plan_hhmm, linie.replace(" ", "").upper()), []):
                if ht not in alle_meldungen:
                    alle_meldungen.append(ht)
            ist_bau = ersatz or any(any(k in m.lower() for k in BAU_KEYWORDS) for m in alle_meldungen)
            if ist_bau:
                aktive_baumeldungen += [m for m in alle_meldungen if any(k in m.lower() for k in BAU_KEYWORDS)]

            schluessel = _g(e, "journeyID", "journeyId", "id") or (plan_hhmm, linie, ziel_geplant)
            if str(schluessel) in gesehen:
                continue
            gesehen.add(str(schluessel))

            reihung, reihung_url = (None, "")
            if not is_cancelled and not ersatz and num:
                reihung, reihung_url = hole_wagenreihung(cat, num, linie, eva_id, p_time, sektoren_aus_gleis)

            if gleiswechsel:
                alle_meldungen.insert(0, f"Heute von Gleis {gleis_aktuell} (statt Gleis {gleis_geplant})")
            if ziel_aktuell != ziel_geplant and not is_cancelled:
                alle_meldungen.insert(0, f"Fährt heute nur bis {ziel_aktuell}")
            if entfallende_halte and not is_cancelled:
                alle_meldungen.append(f"Halt entfällt in: {', '.join(entfallende_halte[:4])}")
            if is_cancelled and not alle_meldungen:
                alle_meldungen.append("Fahrt fällt heute aus")
            diff = int((e_time - p_time).total_seconds() / 60)

            verbindungen.append({
                "sort_ts": e_time.timestamp(),
                "zeit": plan_hhmm,
                "echte_zeit": e_time.strftime("%H:%M"),
                "linie": linie,
                "zug_nr": zug_nr,
                "fahrt_nr": num,
                "kategorie": cat,
                "ziel": ziel_aktuell[:25],
                "ziel_geplant": ziel_geplant[:25],
                "via": via_halte,
                "entfallende_halte": entfallende_halte,
                "gleis": gleis_aktuell,
                "gleis_geplant": gleis_geplant,
                "gleiswechsel": gleiswechsel,
                "sektoren": (reihung.get("sektoren") if reihung else "") or sektoren_aus_gleis,
                "zug_modell": reihung.get("modell", "") if reihung else "",
                "formation": reihung.get("formation", "") if reihung else "",
                "zugteile": reihung.get("zugteile", []) if reihung else [],
                "wagenreihung": reihung.get("wagen", []) if reihung else [],
                "wagenreihung_text": reihung.get("text", "") if reihung else "Keine Wagenreihung verfügbar",
                "reihung_quelle": "live" if reihung else "keine",
                "reihung_richtung": reihung.get("richtung", "") if reihung else "",
                "reihung_url": reihung_url,
                "info": "FÄLLT AUS" if is_cancelled else (f"SEV (+{diff})" if ersatz and diff > 0 else
                         "SEV" if ersatz else (f"+{diff}" if diff > 0 else "pünktlich")),
                "begruendung": " +++ ".join(dict.fromkeys(alle_meldungen)),
                "meldungen": list(dict.fromkeys(alle_meldungen)),
                "bauarbeiten": ist_bau,
                "defekte_aufzuege": alle_defekte,
                "echtzeit": time_type != "SCHEDULE",
            })
        except Exception as ex:
            print(f"  OpenBoards-Eintrag übersprungen @ {eva_id}: {type(ex).__name__}: {ex}")

    if roh and not verbindungen:
        hinweis = "" if OB_STATE["format_warnung"] else \
            " – bitte 'python3 fetch_all_stations.py --probe 8013389' ausführen und mir die Datei schicken"
        OB_STATE["format_warnung"] = True
        raise OpenBoardsFehler(f"OpenBoards-Antwortformat nicht erkannt{hinweis}")

    aktive_baumeldungen = list(dict.fromkeys(aktive_baumeldungen))
    station_ticker = baue_kompletten_ticker(eva_id, station_msgs, aktive_baumeldungen, alle_defekte)
    GLOBAL_STATION_INFOS[eva_id] = {
        "eva": eva_id,
        "ticker": station_ticker,
        "defekte_aufzuege": alle_defekte,
        "bauarbeiten_aktiv": bool(aktive_baumeldungen or station_msgs),
        "baumeldungen": aktive_baumeldungen,
        "alkoholverbot": eva_id in ALKOHOLVERBOT_STATIONEN,
        "quelle": "Deutsche Bahn (OpenBoards)",
        "update": jetzt.strftime("%H:%M")
    }
    ticker_str = " +++ ".join(station_ticker)
    verbindungen.sort(key=lambda x: x["sort_ts"])
    for v in verbindungen:
        v.pop("sort_ts", None)
        v["station_ticker"] = ticker_str
        v["update"] = jetzt.strftime("%H:%M")
    return verbindungen


def hole_station_daten_auto(eva_id):
    """OpenBoards bevorzugt, bei Problemen automatisch Timetables."""
    if DATENQUELLE == "openboards" and not OB_STATE["aus"]:
        try:
            return hole_station_daten_openboards(eva_id), "OpenBoards"
        except OpenBoardsFehler as e:
            if e.status in (401, 403):
                OB_STATE["aus"], OB_STATE["grund"] = True, str(e)
                print(f"!! OpenBoards abgelehnt ({e}). Ist OpenBoards im DB API Marketplace für deine "
                      f"Anwendung abonniert? Nutze bis zum Neustart Timetables.")
            else:
                print(f"  [{eva_id}] {e} – nutze diese Runde Timetables")
    return hole_station_daten(eva_id), "Timetables"


def probe_openboards(eva_id):
    """Speichert eine rohe OpenBoards-Antwort zum Prüfen des Formats."""
    antwort = ob_post(ob_anfrage(eva_id, datetime.now(ZoneInfo("Europe/Berlin"))))
    pfad = f"openboards_probe_{eva_id}.json"
    schreibe_json(pfad, antwort, indent=2)
    eintraege = _ob_eintraege(antwort)
    print(f"Gespeichert: {pfad} – {len(eintraege)} Einträge")
    if isinstance(antwort, dict):
        print("Oberste Felder:", list(antwort.keys()))
    if eintraege:
        print("Felder im 1. Eintrag:", list(eintraege[0].keys()) if isinstance(eintraege[0], dict) else type(eintraege[0]))
        print("Test-Auswertung:")
        for v in hole_station_daten_openboards(eva_id)[:5]:
            print(f"  {v['zeit']} {v['linie']:<10} {v['ziel']:<25} Gl. {v['gleis']:<4} {v['info']}")


def verarbeite_station(item):
    name, eva_id = item
    try:
        daten, quelle = hole_station_daten_auto(eva_id)
        mit_reihung = sum(1 for z in daten if z.get("zugteile"))
        schreibe_json(f"{name}.json", daten)
        print(f"[{name}] {len(daten)} Züge gespeichert ({mit_reihung} mit echter Live-Wagenreihung) [{quelle}]")
    except ApiFehler as e:
        print(f"[{name}] API-Fehler ({e}) – alte JSON bleibt erhalten")
    except Exception as e:
        print(f"[{name}] FEHLER: {type(e).__name__}: {e} – alte JSON bleibt erhalten")


def erzeuge_global_info():
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    wetter_str = "⛅ --°C"
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=51.96&longitude=12.08&current_weather=true", timeout=5)
        if w_res.status_code == 200:
            cw = w_res.json().get("current_weather", {})
            temp, wcode = round(cw.get("temperature", 0)), cw.get("weathercode", 0)
            icon = "☀️" if wcode == 0 else ("⛅" if wcode in (1, 2, 3) else ("🌧️" if wcode < 70 else "❄️"))
            wetter_str = f"{icon} {temp}°C"
    except Exception:
        pass

    bau_count = sum(1 for v in GLOBAL_STATION_INFOS.values() if v.get("bauarbeiten_aktiv"))
    global_data = {
        "title": f"Betriebsinformation ({bau_count} Bahnhöfe mit Meldungen)" if bau_count > 0 else "Regelbetrieb im Streckennetz",
        "wetter": wetter_str,
        "nachricht": f"Aktuell liegen an {bau_count} überwachten Stationen Meldungen zu Bauarbeiten oder Fahrplanänderungen vor." if bau_count > 0 else "Alle überwachten Bahnhöfe melden regulären Betrieb.",
        "update": jetzt.strftime("%H:%M")
    }
    schreibe_json("global_info.json", global_data)
    schreibe_json("station_infos.json", GLOBAL_STATION_INFOS)


def hole_routing_verbindungen(start_id, ziel_id, dateiname):
    if HAFAS_TIMEOUT_COUNT >= 2:
        return
    tz = ZoneInfo("Europe/Berlin")
    jetzt = datetime.now(tz)
    try:
        res = requests.get("https://v6.vbb.transport.rest/journeys", params={"from": start_id, "to": ziel_id, "results": 4, "language": "de", "remarks": "true"}, timeout=4)
        if res.status_code != 200:
            return
        verbindungs_liste = []
        for journey in res.json().get("journeys", []):
            legs = journey.get("legs", [])
            if not legs:
                continue
            first_leg, last_leg = legs[0], legs[-1]
            abfahrt = (first_leg.get("departure") or "")[11:16] or "--:--"
            ankunft = (last_leg.get("arrival") or "")[11:16] or "--:--"
            delay = first_leg.get("departureDelay")
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
                "linie": (first_leg.get("line") or {}).get("name", "Fußweg"),
                "gleis": first_leg.get("departurePlatform") or "-",
                "info": f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich",
                "umstiege": len(legs) - 1,
                "hinweise": " | ".join(dict.fromkeys(remarks[:2])),
                "update": jetzt.strftime("%H:%M")
            })
        if verbindungs_liste:
            schreibe_json(f"{dateiname}.json", verbindungs_liste)
    except Exception:
        pass


def drucke_reihung_statistik():
    print("-" * 60)
    if REIHUNG_STATS:
        print("Wagenreihung Statistik: " + ", ".join(f"{k}={v}" for k, v in sorted(REIHUNG_STATS.items())))
    if bahn_ist_blockiert():
        rest = int(BAHN_STATE["blocked_until"] - time.time())
        print(f"bahn.de-Pause aktiv: noch {rest // 60}:{rest % 60:02d} min")
    print("-" * 60)


def fuehre_runde_aus():
    """Eine komplette Runde. Setzt die Pro-Runde-Zähler zurück."""
    global LIVE_QUERIES_THIS_ROUND, HAFAS_TIMEOUT_COUNT, BUDGET_HIT_IN_STATION
    LIVE_QUERIES_THIS_ROUND = 0
    HAFAS_TIMEOUT_COUNT = 0
    BUDGET_HIT_IN_STATION = False
    with STATS_LOCK:
        REIHUNG_STATS.clear()
        REIHUNG_DIAG.clear()
    raeume_plan_cache_auf()

    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(verarbeite_station, list(STATIONS.items())))
    erzeuge_global_info()
    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
    speichere_reihung_cache()
    drucke_reihung_statistik()


if __name__ == "__main__":
    if "--probe" in sys.argv:
        idx = sys.argv.index("--probe")
        probe_openboards(sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "8013389")
        sys.exit(0)
    lade_reihung_cache()
    if "--loop" in sys.argv:
        runde = 0
        while True:
            runde += 1
            start = time.monotonic()
            print(f"\n================ RUNDE {runde} ({datetime.now().strftime('%H:%M:%S')}) ================")
            try:
                fuehre_runde_aus()
            except Exception as e:
                print(f"Runde abgebrochen: {type(e).__name__}: {e}")
            dauer = time.monotonic() - start
            print(f"Runde dauerte {dauer:.0f}s. Nächstes Update in {LOOP_PAUSE} Sekunden...")
            time.sleep(LOOP_PAUSE)
    else:
        fuehre_runde_aus()
