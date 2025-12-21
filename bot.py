import requests
from bs4 import BeautifulSoup
import json
import time

URL = "https://www.bahnhof.de/zerbst-anhalt/abfahrt"

def hole_daten():
    try:
        # Wir tarnen den Bot als echten Browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        ergebnis = []
        
        # Auf bahnhof.de liegen die Züge in 'arrival-departure-card' Elementen
        eintraege = soup.find_all('div', class_='arrival-departure-card')

        for eintrag in eintraege[:8]:
            try:
                # Zeit extrahieren
                zeit = eintrag.find('span', class_='arrival-departure-card__time').text.strip()
                # Linie/Zugnummer (z.B. RE 13)
                linie = eintrag.find('span', class_='arrival-departure-card__train-number').text.strip()
                # Zielbahnhof
                ziel = eintrag.find('span', class_='arrival-departure-card__direction').text.strip()
                # Gleis (falls vorhanden)
                gleis_el = eintrag.find('span', class_='arrival-departure-card__platform')
                gleis = gleis_el.text.replace('Gl.', '').strip() if gleis_el else "--"
                # Verspätungsinfo (z.B. "+ 5 min")
                info_el = eintrag.find('span', class_='arrival-departure-card__delay')
                info = info_el.text.strip() if info_el else ""

                ergebnis.append({
                    "zeit": zeit,
                    "linie": linie,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info
                })
            except Exception:
                continue 

        if ergebnis:
            with open('daten.json', 'w', encoding='utf-8') as f:
                json.dump(ergebnis, f, ensure_ascii=False, indent=4)
            print("Erfolgreich von bahnhof.de gelesen.")
            return True
    except Exception as e:
        print(f"Fehler: {e}")
        return False

# 4-Minuten-Schleife für Live-Gefühl
start_zeit = time.time()
while time.time() - start_zeit < 240:
    hole_daten()
    time.sleep(30)
