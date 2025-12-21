import requests
from bs4 import BeautifulSoup
import json
import time

# Die offizielle Seite, die du mir gegeben hast
URL = "https://www.bahnhof.de/zerbst-anhalt/abfahrt"

def hole_daten():
    try:
        # Wir geben uns als Browser aus, damit die Seite uns nicht blockiert
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        ergebnis = []
        
        # Suche nach den Abfahrts-Elementen auf bahnhof.de
        # Wir suchen nach den Containern der einzelnen Züge
        eintraege = soup.select('.arrival-departure-card') # Dies ist die Klasse auf bahnhof.de

        for eintrag in eintraege[:8]:
            try:
                zeit = eintrag.select_one('.arrival-departure-card__time').text.strip()
                linie = eintrag.select_one('.arrival-departure-card__train-number').text.strip()
                ziel = eintrag.select_one('.arrival-departure-card__direction').text.strip()
                # Gleis finden
                gleis_el = eintrag.select_one('.arrival-departure-card__platform')
                gleis = gleis_el.text.replace('Gl.', '').strip() if gleis_el else "--"
                
                # Verspätung/Info checken
                info_el = eintrag.select_one('.arrival-departure-card__delay')
                info = info_el.text.strip() if info_el else ""

                ergebnis.append({
                    "zeit": zeit,
                    "linie": linie,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info
                })
            except:
                continue # Falls ein Feld fehlt, nimm den nächsten Zug

        if ergebnis:
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(ergebnis, f, ensure_ascii=False, indent=4)
            return True
    except Exception as e:
        print(f"Fehler beim Scrapen von bahnhof.de: {e}")
        return False

# 4-Minuten-Schleife für die 30-Sekunden-Updates
start_zeit = time.time()
while time.time() - start_zeit < 240: 
    if hole_daten():
        print("Live-Daten von bahnhof.de geholt...")
    time.sleep(30)
