import os
import re
import glob
import json
import subprocess
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO_DIR = "/home/erik/Abfahrtstafel-"
os.chdir(REPO_DIR)

import fetch_all_stations as fas

INTERVALL_SEKUNDEN = 90
PROFILE_DIR = "/home/erik/.config/chromium-real-profile"
EXT_DIR = "/home/erik/bahn_ext"
TRAIN_CACHE_FILE = "/home/erik/Abfahrtstafel-/.permanent_train_cache.json"

CURRENT_TASK = None
TASK_RESULT = {}
TASK_EVENT = threading.Event()
BRIDGE_LOCK = threading.Lock()
LAST_POLL_TS = 0.0

def sync_filter_with_internal_cache():
    """Übernimmt alle bereits in fetch_all_stations gecachten Züge direkt in den permanenten Zugnummern-Filter."""
    heute = datetime.now().strftime("%Y-%m-%d")
    for k, entry in list(fas.ZUG_FORMATION_CACHE.items()):
        if isinstance(entry, dict) and entry.get("status") == "ok" and entry.get("data"):
            m = re.search(r"(\d{3,6})", str(k))
            if m:
                t_key = f"ZUG_{m.group(1)}_{heute}"
                fas.PERMANENT_TRAIN_CACHE[t_key] = entry["data"]

def load_permanent_filter():
    if os.path.exists(TRAIN_CACHE_FILE):
        try:
            with open(TRAIN_CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            heute = datetime.now().strftime("%Y-%m-%d")
            trains = raw.get("trains", raw) if isinstance(raw, dict) else {}
            no_reihung = raw.get("no_reihung", []) if isinstance(raw, dict) else []
            for k, v in trains.items():
                if heute in k:
                    # Alten Key-Stil ("16140_2026-11-09") automatisch auf neuen Stil ("ZUG_16140_2026-11-09") heben
                    clean_k = k if k.startswith("ZUG_") else f"ZUG_{k}"
                    fas.PERMANENT_TRAIN_CACHE[clean_k] = v
            for k in no_reihung:
                if heute in k:
                    clean_k = k if k.startswith("ZUG_") else f"ZUG_{k}"
                    fas.NO_REIHUNG_CACHE.add(clean_k)
        except Exception:
            pass
    sync_filter_with_internal_cache()
    print(f"[Filter] {len(fas.PERMANENT_TRAIN_CACHE)} Züge mit Reihung + {len(fas.NO_REIHUNG_CACHE)} ohne Reihung aktiv (werden nicht erneut abgefragt).")

def save_permanent_filter():
    try:
        sync_filter_with_internal_cache()
        heute = datetime.now().strftime("%Y-%m-%d")
        payload = {
            "trains": {k: v for k, v in fas.PERMANENT_TRAIN_CACHE.items() if heute in k},
            "no_reihung": [k for k in fas.NO_REIHUNG_CACHE if heute in k]
        }
        with open(TRAIN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        pass

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "https://www.bahn.de")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        global CURRENT_TASK, LAST_POLL_TS
        LAST_POLL_TS = time.time()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        with BRIDGE_LOCK:
            task = CURRENT_TASK
            CURRENT_TASK = None
        self.wfile.write(json.dumps(task or {}).encode("utf-8"))

    def do_POST(self):
        global TASK_RESULT
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw)
            TASK_RESULT = data
            TASK_EVENT.set()
        except Exception:
            pass
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")

def browser_fetch(url):
    global CURRENT_TASK, TASK_RESULT
    task_id = str(uuid.uuid4())
    TASK_EVENT.clear()
    with BRIDGE_LOCK:
        CURRENT_TASK = {"id": task_id, "url": url}
    if TASK_EVENT.wait(timeout=12.0):
        return TASK_RESULT.get("status", 0), TASK_RESULT.get("body", "")
    return 0, "Timeout (Browser-Tab antwortet nicht)"

fas.BRIDGE_FUNC = browser_fetch

def wait_for_internet():
    while True:
        try:
            res = subprocess.run(["ping", "-c", "1", "-W", "2", "8.8.8.8"], capture_output=True)
            if res.returncode == 0:
                return
        except Exception:
            pass
        print("Warte auf aktive Internetverbindung...")
        time.sleep(3)

def simulate_human_interaction(reload_page=False):
    try:
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        subprocess.run(["xdotool", "mousemove", "420", "360"], env=env, check=False)
        time.sleep(0.2)
        subprocess.run(["xdotool", "mousemove", "640", "410"], env=env, check=False)
        time.sleep(0.2)
        subprocess.run(["xdotool", "click", "1"], env=env, check=False)
        if reload_page:
            subprocess.run(["xdotool", "key", "F5"], env=env, check=False)
            time.sleep(4.0)
        subprocess.run(["xdotool", "key", "Page_Down"], env=env, check=False)
        time.sleep(0.4)
        subprocess.run(["xdotool", "key", "Page_Up"], env=env, check=False)
    except Exception:
        pass

def start_real_chromium():
    subprocess.run(["pkill", "-f", "chromium-real-profile"], check=False)
    time.sleep(1)
    prefs_file = f"{PROFILE_DIR}/Default/Preferences"
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                p = json.load(f)
            p.setdefault("profile", {})["exit_type"] = "Normal"
            with open(prefs_file, "w", encoding="utf-8") as f:
                json.dump(p, f)
        except Exception:
            pass

    chrome_bin = "/usr/bin/chromium" if os.path.exists("/usr/bin/chromium") else "/usr/bin/chromium-browser"
    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    print("Starte echten System-Chromium...")
    subprocess.Popen([
        chrome_bin,
        f"--user-data-dir={PROFILE_DIR}",
        f"--load-extension={EXT_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "https://www.bahn.de/buchung/fahrplan/suche"
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(30):
        if time.time() - LAST_POLL_TS < 3.0:
            break
        time.sleep(1)

    time.sleep(3)
    simulate_human_interaction()
    time.sleep(2)
    print("Echter Browser verbunden!")

def update_heartbeat_timestamp():
    """Schreibt den aktuellen Sekunden-Zeitstempel in global_info.json, damit jede Runde ein frisches Live-Update pusht."""
    gi_path = os.path.join(REPO_DIR, "global_info.json")
    try:
        data = {}
        if os.path.exists(gi_path):
            with open(gi_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        if isinstance(data, dict):
            data["last_live_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(gi_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def git_push():
    try:
        update_heartbeat_timestamp()
        json_files = [
            os.path.basename(f) for f in glob.glob(os.path.join(REPO_DIR, "*.json"))
            if not os.path.basename(f).startswith(".") and os.path.basename(f) != "daten.json"
        ]
        if not json_files:
            return

        zeit = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "-C", REPO_DIR, "fetch", "origin", "main"], check=False)
        subprocess.run(["git", "-C", REPO_DIR, "reset", "--soft", "origin/main"], check=False)
        subprocess.run(["git", "-C", REPO_DIR, "add"] + json_files, check=False)

        diff = subprocess.run(["git", "-C", REPO_DIR, "status", "--porcelain"] + json_files, capture_output=True, text=True)
        if diff.stdout.strip():
            subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", f"Live Update ({zeit})"], check=False)
            res = subprocess.run(["git", "-C", REPO_DIR, "push", "origin", "main", "--force"], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"[{zeit}] >>> ABFAHRTSDATEN & REIHUNGEN ERFOLGREICH AUF GITHUB AKTUALISIERT! <<<")
            else:
                print(f"Git-Push Fehler: {res.stderr}")
        else:
            print("Keine Änderungen in den JSON-Dateien.")
    except Exception as e:
        print(f"Git-Upload-Fehler: {e}")

def main():
    wait_for_internet()
    fas.lade_reihung_cache()
    load_permanent_filter()

    server = HTTPServer(("127.0.0.1", 8765), BridgeHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    start_real_chromium()
    last_refresh = time.time()
    runde = 1
    station_list = list(fas.STATIONS.items())
    next_station_idx = 0

    while True:
        start_ts = time.time()
        ordered = station_list[next_station_idx:] + station_list[:next_station_idx]
        start_station_name = station_list[next_station_idx][0]

        print(f"\n================ RUNDE {runde} ({datetime.now().strftime('%H:%M:%S')}) ================")
        print(f"[Aktualisiere Abfahrtsdaten aller 23 Bahnhöfe | Wagenreihungs-Fokus ab #{next_station_idx + 1}: {start_station_name}]")
        try:
            wait_for_internet()
            if time.time() - LAST_POLL_TS > 10 or time.time() - last_refresh > 900:
                start_real_chromium()
                last_refresh = time.time()
            elif fas.BAHN_STATE.get("blocked"):
                print("[Browser] Akamai-Pause erkannt -> Lade bahn.de per F5 frisch...")
                simulate_human_interaction(reload_page=True)
            else:
                simulate_human_interaction(reload_page=False)

            fas.BAHN_STATE["blocks_in_row"] = 0
            fas.BAHN_STATE["blocked"] = False
            fas.LIVE_QUERIES_THIS_ROUND = 0
            fas.REIHUNG_STATS.clear()
            fas.REIHUNG_DIAG.clear()
            fas.HAFAS_TIMEOUT_COUNT = 0

            first_unfinished_idx = None

            # Alle 23 Bahnhöfe bekommen in jeder Runde frische Abfahrtszeiten & Verspätungen!
            for offset, station_item in enumerate(ordered):
                real_idx = (next_station_idx + offset) % len(station_list)
                fas.BUDGET_HIT_IN_STATION = False
                fas.verarbeite_station(station_item)

                if fas.BUDGET_HIT_IN_STATION and first_unfinished_idx is None:
                    first_unfinished_idx = real_idx

                time.sleep(0.2)

            if first_unfinished_idx is not None:
                next_station_idx = first_unfinished_idx
                print(f"[Wagenreihung-Fortschritt] {fas.LIVE_QUERIES_THIS_ROUND} neue Züge abgefragt -> Nächste Runde prüft weiter ab: {station_list[next_station_idx][0]}")
            else:
                next_station_idx = 0
                if fas.LIVE_QUERIES_THIS_ROUND == 0:
                    print("[Wagenreihung-Ruhemodus] Alle aktuellen Züge haben bereits ihre Wagenreihung -> 0 Anfragen an bahn.de nötig (nur Abfahrtszeiten frisch geladen)!")
                else:
                    print(f"[Wagenreihung-Komplett] Alle Bahnhöfe durch ({fas.LIVE_QUERIES_THIS_ROUND} neue Züge geladen) -> Überwache ab nächster Runde wieder von vorne ({station_list[0][0]}) auf neue Züge.")

            fas.erzeuge_global_info()
            fas.hole_routing_verbindungen("733238", "8013389", "verbindungen_bauhof_bahnhof")
            fas.hole_routing_verbindungen("733238", "8010224", "verbindungen_bauhof_magdeburg")
            fas.speichere_reihung_cache()
            save_permanent_filter()
            fas.drucke_reihung_statistik()
            print(f"[Gedächtnis] {len(fas.PERMANENT_TRAIN_CACHE)} Züge mit Reihung | {len(fas.NO_REIHUNG_CACHE)} ohne Reihung gespeichert.")

            git_push()

        except Exception as e:
            print(f"Fehler in der Hauptschleife: {e}")

        runde += 1
        dauer = int(time.time() - start_ts)
        wartezeit = max(15, INTERVALL_SEKUNDEN - dauer)
        print(f"Runde dauerte {dauer}s. Nächstes Echtzeit-Update in {wartezeit} Sekunden...")
        time.sleep(wartezeit)

if __name__ == "__main__":
    main()
