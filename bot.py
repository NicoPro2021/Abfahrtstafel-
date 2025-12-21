import requests
from bs4 import BeautifulSoup
import json

# Die echte Webseite für Zerbst/Anhalt
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?input=Zerbst&boardType=dep&start=yes"

def scrape_bahn():
    try:
        # Website aufrufen
        response = requests.get(URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        fahrplan = []
        # Suche alle Zeilen der Abfahrtstabelle
        rows = soup.find_all('tr', id=lambda x: x and x.startswith('tr_res_'))

        for row in rows[:5]: # Die nächsten 5 Abfahrten
            # Zeit extrahieren
            zeit_raw = row.find('td', class_='time')
            zeit = zeit_raw.get_text(strip=True) if zeit_raw else "--:--"

            # Linie extrahieren (z.B. RE 13)
            linie_raw = row.find('td', class_='train')
            linie = linie_raw.get_text(strip=True).replace(" ", "") if linie_raw else "???"

            # Ziel extrahieren
            ziel_raw = row.find('td', class_='route')
            # Nur das letzte Wort/Ziel nehmen
            ziel = ziel_raw.get_text(" ", strip=True).split("  ")[-1].strip() if ziel_raw else "Unbekannt"

            # Gleis extrahieren
            gleis_raw = row.find('td', class_='platform')
            gleis = gleis_raw.get_text(strip=True) if gleis_raw else "-"

            # Info / Verspätung / Ausfall
            info_raw = row.find('td', class_='ris')
            info = info_raw.get_text(" ", strip=True) if info_raw else ""

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info
            })
            
        return fahrplan
    except Exception as e:
        print(f"Fehler beim Scraping: {e}")
        return []

# Daten holen und als daten.json speichern
data = scrape_bahn()
if data:
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Daten erfolgreich von DB-Webseite geholt!")
else:
    print("Keine Daten gefunden. Überprüfe die URL oder Struktur.")
