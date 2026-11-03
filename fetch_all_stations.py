import re
import sys
import socket
import subprocess
import threading
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

# DEINE ZUGANGSDATEN
CLIENT_ID = "647fddb98582bec8984c65e1256eb617"
CLIENT_SECRET = "6af72e24106f2250967364fac780bbe6"

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

# Zugnummern auf dem RE 13, die planmäßig als Doppeltraktion (2x 3-Teiler) verkehren
RE13_DOPPELTRAKTION_NUMMERN = {"16136", "16112", "16115", "16116", "16119", "16120", "16123", "16124", "16127", "16128", "16131", "16132"}

HEADERS_XML = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/xml'}
HEADERS_JSON = {'DB-Client-Id': CLIENT_ID, 'DB-Api-Key': CLIENT_SECRET, 'accept': 'application/json'}

THREAD_LOCAL = threading.local()
CACHE_LOCK = threading.Lock()

GLOBAL_STATION_INFOS = {}
ZUG_FORMATION_CACHE = {}
AUFZUG_CACHE = {}
HAFAS_TIMEOUT_COUNT = 0
DIAGNOSE_COUNT = 0


def is_warp_proxy_active():
    """Prüft, ob der lokale Cloudflare WARP SOCKS5-Proxy auf Port 40000 läuft."""
    try:
        with socket.create_connection(("127.0.0.1", 40000), timeout=0.3):
            return True
    except Exception:
        return False


WARP_ACTIVE = is_warp_proxy_active()
if WARP_ACTIVE:
    print("[Info] Cloudflare WARP Proxy (Port 40000) erkannt -> Live-Abfragen über WARP aktiv.")


def get_thread_cffi_session():
    if not hasattr(THREAD_LOCAL, "cffi_session"):
        try:
            s = cffi_requests.Session(impersonate="chrome")
        except Exception:
            s = requests.Session()
        if WARP_ACTIVE:
            s.proxies = {
                "http": "socks5h://127.0.0.1:40000",
                "https": "socks5h://127.0.0.1:40000"
            }
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


def teile_gekuppelte_triebzuege_auf(gruppe_wagen, ist_regio=True):
    """
    Teilt gekuppelte Triebzüge (z.B. 2x 3-Teiler = 6 Wagen, 3er+5er = 8 Wagen, 2x 5-Teiler = 10 Wagen)
    an der Kupplungsstelle in separate Zugteile auf.
    """
    n = len(gruppe_wagen)
    if n < 4:
        return [gruppe_wagen]

    # 1. Prüfen auf explizite Steuerwagen-Paare oder 2+1 Endwagen in der Mitte
    teile = []
    aktueller_teil = []
    for idx, w in enumerate(gruppe_wagen):
        aktueller_teil.append(w)
        if 2 <= len(aktueller_teil) and idx < n - 2:
            ist_kupplung = (
                (w.get("ist_steuerwagen") and gruppe_wagen[idx + 1].get("ist_steuerwagen"))
                or (ist_regio and w.get("klasse") in ("2+1", "1") and gruppe_wagen[idx + 1].get("klasse") == "2")
            )
            if ist_kupplung:
                teile.append(aktueller_teil)
                aktueller_teil = []
    if aktueller_teil:
        teile.append(aktueller_teil)
    if len(teile) > 1:
        return teile

    # 2. Wenn Regionaltriebzug mit 6 Wagen (2x 3-Teiler) oder 10 Wagen (2x 5-Teiler) in einer Liste liegt
    if ist_regio and n == 6:
        return [gruppe_wagen[:3], gruppe_wagen[3:]]
    if ist_regio and n == 10:
        return [gruppe_wagen[:5], gruppe_wagen[5:]]
    return [gruppe_wagen]


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

    zugteile, flache_wagen_liste, sektoren_alle, baureihen_gefunden, raw_units = [], [], [], [], []
    ist_regio = (cat or "").upper() not in ("ICE", "IC", "EC", "EN", "NJ", "FLX", "D")

    for grp in groups:
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
            raw_vid = re.sub(r"\D", "", str(vehicle.get("vehicleID") or vehicle.get("uic") or ""))
            ist_uic_endwagen = len(raw_vid) == 12 and raw_vid[4:8] in ("0442", "1442", "2442", "3442", "0462", "1462", "0463", "1463")
            ist_steuerwagen = ist_uic_endwagen or any(k in cat_type for k in ("CONTROLCAR", "CONTROL_CAR", "STEUERWAGEN", "POWERCAR"))

            amenities = vehicle.get("amenities") or vehicle.get("ausstattung") or []
            am_types = {str(a.get("type") or a.get("art") or "").upper() for a in amenities if isinstance(a, dict)}
            hat_klima = bool(features.get("airConditioning", True)) if features else (("AIR_CONDITION" in am_types) if amenities else True)
            hat_fahrrad = bool(features.get("bike") or features.get("multiPurpose")) if features else bool(
                v_type.get("hasBikeSpace") or "BIKE_SPACE" in am_types or "MULTI_PURPOSE" in am_types or "BIKE" in cat_type
            )

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

            gruppe_wagen.append({
                "wagen": str(w_nr) if w_nr else "",
                "klasse": klasse,
                "sektor": sektor,
                "klima": hat_klima,
                "fahrrad": hat_fahrrad,
                "rollstuhl": False,
                "wc": True,
                "ist_steuerwagen": ist_steuerwagen
            })

        if gruppe_wagen:
            for einheit in teile_gekuppelte_triebzuege_auf(gruppe_wagen, ist_regio):
                raw_units.append((einheit, ziel_grp))

    if not raw_units:
        return None

    gesamt_einheiten = len(raw_units)
    for idx, (einheit_wagen, ziel_grp) in enumerate(raw_units):
        teil_nr = idx + 1
        for w in einheit_wagen:
            w.pop("ist_steuerwagen", None)
            w["zugteil"] = teil_nr
            flache_wagen_liste.append(w)
        anz = len(einheit_wagen)
        teil_typ = f"{anz}-Teiler" if ist_regio else f"{anz} Wagen"
        zugteile.append({
            "teil_nr": teil_nr,
            "bezeichnung": f"{teil_nr}. Zugteil ({teil_typ})" if gesamt_einheiten > 1 else teil_typ,
            "ziel": ziel_grp,
            "wagen": einheit_wagen
        })

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

    br_str = baureihen_gefunden[0] if baureihen_gefunden else ("Talent 2 (BR 442)" if ist_regio else "")
    zug_modell = f"{br_str} • {formation_str}" if br_str else formation_str
    sektor_str = f"{sektoren_alle[0]}–{sektoren_alle[-1]}" if len(sektoren_alle) > 1 else (sektoren_alle[0] if sektoren_alle else "")

    return {
        "modell": zug_modell,
        "formation": formation_str,
        "sektoren": sektor_str,
        "zugteile": zugteile,
        "wagen": flache_wagen_liste,
        "text": f"{zug_modell} • Sektor {sektor_str}" if sektor_str else zug_modell
    }


def kopiere_formation_fuer_unterwegsbahnhof(cached_reihung, sektoren_aus_gleis):
    neue_zugteile, neue_wagen = [], []
    for z in cached_reihung.get("zugteile", []):
        w_kopie = []
        for w in z.get("wagen", []):
            wc = dict(w)
            if not sektoren_aus_gleis:
                wc["sektor"] = ""
            w_kopie.append(wc)
            neue_wagen.append(wc)
        neue_zugteile.append({
            "teil_nr": z["teil_nr"],
            "bezeichnung": z["bezeichnung"],
            "ziel": z.get("ziel", ""),
            "wagen": w_kopie
        })
    modell = cached_reihung.get("modell", "")
    return {
        "modell": modell,
        "formation": cached_reihung.get("formation", ""),
        "sektoren": sektoren_aus_gleis,
        "zugteile": neue_zugteile,
        "wagen": neue_wagen,
        "text": f"{modell} • Sektor {sektoren_aus_gleis}" if sektoren_aus_gleis else modell
    }


def baue_konsistente_linien_reihung(cat, fahrt_nr, linie, wings, sektoren_aus_gleis, alle_meldungen):
    up_line = (linie or "").upper().strip()
    up_cat = (cat or "").upper().strip()
    meldungen_text = " ".join(alle_meldungen).lower()
    nr_str = str(fahrt_nr).strip()
    nr_int = int(nr_str) if nr_str.isdigit() else 0

    ist_doppeltraktion = bool(
        wings
        or nr_str in RE13_DOPPELTRAKTION_NUMMERN
        or "weiterer wagen" in meldungen_text
        or "zusätzlichen wagen" in meldungen_text
    )

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

    if any(k in up_line for k in ("RE 13", "RE 14", "RB 50", "RB 40", "RB 113", "RE 7", "RB 33", "RB 20", "RB 22")) or up_cat.startswith("S") or up_line.startswith("S "):
        modell_basis = "Talent 2 (BR 442)"
        if ist_doppeltraktion:
            zugteile = [baue_triebzug_einheit(3, 1, 2), baue_triebzug_einheit(3, 2, 2)]
            formation = "2x 3-Teiler (2 Züge)"
        elif "RE 14" in up_line and (nr_int % 2 == 0):
            zugteile = [baue_triebzug_einheit(5, 1, 1)]
            formation = "5-Teiler"
        elif "RE 7" in up_line:
            zugteile = [baue_triebzug_einheit(5, 1, 1)]
            formation = "5-Teiler"
        else:
            zugteile = [baue_triebzug_einheit(3, 1, 1)]
            formation = "3-Teiler"
    elif up_cat == "OE" or up_line.startswith("OE") or up_line in ("RE 1", "RE 8", "RB 10"):
        modell_basis = "ODEG Stadler KISS (BR 445)" if "RE 1" not in up_line else "ODEG Desiro HC (BR 462)"
        anz = 6 if "RE 1" in up_line else 4
        formation = f"{anz}-Teiler"
        zugteile = [baue_triebzug_einheit(anz, 1, 1)]
    elif "FEX" in up_line or up_line in ("RE 3", "RE 4", "RE 5", "RE 20"):
        modell_basis = "Twindexx Vario (BR 445)"
        anz = 4 if "FEX" in up_line or "RE 20" in up_line else 5
        formation = f"{anz}-Teiler"
        zugteile = [baue_triebzug_einheit(anz, 1, 1)]
    elif up_cat in ("ICE", "IC", "EC", "FLX", "D", "EN", "NJ"):
        modell_basis = "ICE 4 (BR 412)" if up_cat == "ICE" else ("Intercity 2" if up_cat in ("IC", "EC") else "Fernzug")
        struktur = ["1", "1", "Bistro", "2", "2", "2", "2"] if up_cat == "ICE" else ["1", "2", "2", "2", "2"]
        formation = f"{len(struktur)} Wagen"
        zugteile = [{
            "teil_nr": 1,
            "bezeichnung": formation,
            "ziel": "",
            "wagen": [
                {"wagen": str(i + 1), "klasse": kl, "sektor": "", "klima": True, "fahrrad": (i == len(struktur) - 1), "rollstuhl": (i == 1), "wc": True, "zugteil": 1}
                for i, kl in enumerate(struktur)
            ]
        }]
    else:
        modell_basis = "Talent 2 (BR 442)"
        formation = "3-Teiler"
        zugteile = [baue_triebzug_einheit(3, 1, 1)]

    flache_wagen = [w for z in zugteile for w in z["wagen"]]
    voll_modell = f"{modell_basis} • {formation}"
    return {
        "modell": voll_modell,
        "formation": formation,
        "sektoren": sektoren_aus_gleis,
        "zugteile": zugteile,
        "wagen": flache_wagen,
        "text": f"{voll_modell} • Sektor {sektoren_aus_gleis}" if sektoren_aus_gleis else voll_modell
    }


def hole_wagenreihung(cat, fahrt_nr, linie, eva_id, p_time_berlin, trip_id, wings, sektoren_aus_gleis, alle_meldungen, tz):
    global DIAGNOSE_COUNT
    if not fahrt_nr:
        return None, ""

    init_time_berlin = p_time_berlin
    m_init = re.search(r"-(\d{10})-\d+$", str(trip_id or ""))
    if m_init:
        try:
            init_time_berlin = datetime.strptime(m_init.group(1), "%y%m%d%H%M").replace(tzinfo=tz)
        except Exception:
            pass

    zug_tag_key = (str(fahrt_nr), init_time_berlin.strftime("%Y-%m-%d"))
    utc_time = p_time_berlin.astimezone(timezone.utc)
    iso_time = utc_time.strftime("%Y-%m-%dT%H:%M:00.000Z")
    date_str = p_time_berlin.strftime("%Y-%m-%d")

    lookup_eva = MAIN_EVA_MAP.get(str(eva_id), str(eva_id))
    primary_cat = cat or (linie.split()[0].upper() if linie else "RE")
    if primary_cat == "OE" and linie:
        first_w = linie.split()[0].upper()
        if first_w in ("RE", "RB"):
            primary_cat = first_w

    primary_bahn_url = (
        "https://www.bahn.de/web/api/reisebegleitung/wagenreihung/vehicle-sequence"
        f"?administrationId=80"
        f"&category={urllib.parse.quote(str(primary_cat))}"
        f"&date={date_str}"
        f"&evaNumber={lookup_eva}"
        f"&number={urllib.parse.quote(str(fahrt_nr))}"
        f"&time={iso_time}"
    )

    with CACHE_LOCK:
        if zug_tag_key in ZUG_FORMATION_CACHE:
            return kopiere_formation_fuer_unterwegsbahnhof(ZUG_FORMATION_CACHE[zug_tag_key], sektoren_aus_gleis), primary_bahn_url

    session = get_thread_cffi_session()

    # Live-Abruf von www.bahn.de (läuft auf GitHub Actions über den lokalen Cloudflare WARP Proxy)
    try:
        res = session.get(
            primary_bahn_url,
            headers={"Accept": "application/json", "Referer": "https://www.bahn.de/"},
            timeout=4
        )
        if DIAGNOSE_COUNT < 4:
            DIAGNOSE_COUNT += 1
            print(f"[Diagnose bahn.de] {linie} ({fahrt_nr}) @ {lookup_eva}: HTTP {res.status_code}")

        if res.status_code == 200 and res.text.strip().startswith("{"):
            parsed = parse_wagenreihung_json(res.json(), primary_cat)
            if parsed:
                if not parsed["sektoren"] and sektoren_aus_gleis:
                    parsed["sektoren"] = sektoren_aus_gleis
                with CACHE_LOCK:
                    ZUG_FORMATION_CACHE[zug_tag_key] = parsed
                print(f"  -> [Live-Wagenreihung OK] {linie} ({fahrt_nr}): {parsed['modell']}")
                return parsed, primary_bahn_url
    except Exception as e:
        if DIAGNOSE_COUNT < 4:
            DIAGNOSE_COUNT += 1
            print(f"[Diagnose bahn.de Fehler]: {e}")

    konsistent = baue_konsistente_linien_reihung(cat, fahrt_nr, linie, wings, sektoren_aus_gleis, alle_meldungen)
    with CACHE_LOCK:
        ZUG_FORMATION_CACHE[zug_tag_key] = konsistent
    return konsistent, primary_bahn_url


def hole_defekte_aufzuege(eva_id):
    lookup_eva = MAIN_EVA_MAP.get(str(eva_id), str(eva_id))
    if lookup_eva in AUFZUG_CACHE:
        return AUFZUG_CACHE[lookup_eva]
    defekte = []
    try:
        st_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations?eva={lookup_eva}"
        st_res = requests.get(st_url, headers=HEADERS_JSON, timeout=3.5)
        if st_res.status_code == 200:
            res_list = st_res.json().get("result", [])
            if res_list and res_list[0].get("number"):
                fa_url = f"https://apis.deutschebahn.com/db-api-marketplace/apis/fasta/v2/stations/{res_list[0]['number']}"
                fa_res = requests.get(fa_url, headers=HEADERS_JSON, timeout=3.5)
                if fa_res.status_code == 200:
                    for fac in fa_res.json().get("facilities", []):
                        if fac.get("state") == "INACTIVE":
                            f_type = "Aufzug" if fac.get("type") == "ELEVATOR" else "Rolltreppe"
                            desc = fac.get("description") or f"Anlage {fac.get('equipmentnumber', '')}"
                            defekte.append(f"🛗 {f_type} außer Betrieb ({desc})")
    except Exception:
        pass
    res_unique = list(dict.fromkeys(defekte))
    AUFZUG_CACHE[lookup_eva] = res_unique
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
            cat, num, line_attr = tl.get('c', ''), tl.get('n', ''), dp.get('l', '')
            linie = format_linienname(cat, line_attr, num)
            zug_nr = f"{cat} {num}".strip()
            wings = dp.get('wings') or chg.get('wings') or ""

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
                reihung, reihung_url = hole_wagenreihung(cat, num, linie, eva_id, p_time, trip_id, wings, sektoren_aus_gleis, alle_meldungen, tz)

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
                "wagenreihung_text": reihung.get("text", "") if reihung else "",
                "reihung_url": reihung_url,
                "info": "FÄLLT AUS" if is_cancelled else (f"+{diff}" if diff > 0 else "pünktlich"),
                "begruendung": " +++ ".join(dict.fromkeys(alle_meldungen)),
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
    changes, station_msgs, aktive_baumeldungen = {}, [], []

    zug_freitexte, hafas_ticker, defekte_hafas = hole_live_hafas_meldungen(eva_id)
    station_msgs.extend(hafas_ticker)
    alle_defekte = list(dict.fromkeys(hole_defekte_aufzuege(eva_id) + defekte_hafas))

    try:
        c_res = requests.get(f"https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1/fchg/{eva_id}", headers=HEADERS_XML, timeout=10)
        if c_res.status_code == 200:
            root = ET.fromstring(c_res.content)
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
    mit_reihung = sum(1 for z in daten if z.get("zugteile"))
    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
    print(f"[{name}] {len(daten)} Züge gespeichert ({mit_reihung} mit Wagenreihung)")


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
    with open("global_info.json", "w", encoding="utf-8") as f:
        json.dump(global_data, f, ensure_ascii=False, indent=4)
    with open("station_infos.json", "w", encoding="utf-8") as f:
        json.dump(GLOBAL_STATION_INFOS, f, ensure_ascii=False, indent=4)


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
            abfahrt = first_leg.get("departure", "")[11:16] or "--:--"
            ankunft = last_leg.get("arrival", "")[11:16] or "--:--"
            delay = first_leg.get("departureDelay")
            verbindungs_liste.append({
                "abfahrt": abfahrt,
                "ankunft": ankunft,
                "linie": (first_leg.get("line") or {}).get("name", "Fußweg"),
                "gleis": first_leg.get("departurePlatform") or "-",
                "info": f"+{int(delay/60)}" if delay and delay > 0 else "pünktlich",
                "umstiege": len(legs) - 1,
                "update": jetzt.strftime("%H:%M")
            })
        with open(f"{dateiname}.json", 'w', encoding='utf-8') as f:
            json.dump(verbindungs_liste, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


if __name__ == "__main__":
    station_items = list(STATIONS.items())
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(verarbeite_station, station_items)
    erzeuge_global_info()
    hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
    hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
