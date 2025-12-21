import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Die URL für die Abfahrtstafel Zerbst/Anhalt
# boardType=dep steht für Abfahrten (Departures)
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?input=Zerbst&boardType=dep&start=yes"

def scrape_bahn_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 1. Webseite laden
        print(f"Lade Daten von: {URL}")
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []
        
        # 2. Suche die Tabellenzeilen für die Abfahrten
        # Die Bahn nutzt IDs wie 'tr_res_0', 'tr_res_1' usw.
        rows = soup.find_all('tr', id=lambda x: x and x.startswith('tr_res_'))

        for row in rows[:6]: # Die nächsten 6 Abfahrten verarbeiten
            # Zeit extrahieren
            zeit_tag = row.find('td', class_='time')
            zeit = zeit_tag.get_text(strip=True) if zeit_tag else "--:--"

            # Linie extrahieren (z.B. "RE 13")
            linie_tag = row.find('td', class_='train')
            linie = linie_tag.get_text(strip=True).replace(" ", "") if linie_tag else "???"

            # Ziel extrahieren (Der letzte Ort in der Route)
            ziel_tag = row.find('td', class_='route')
            if ziel_tag:
                # Die Route enthält oft Zwischenhalte, wir nehmen den letzten
                ziel_text = ziel_tag.get_text(" ", strip=True)
                ziel = ziel_text.split("  ")[-1].strip()
            else:
                ziel = "Unbekannt"

            # Gleis extrahieren
            gleis_tag = row.find('td', class_='platform')
            gleis = gleis_tag.get_text(strip=True) if gleis_tag else "-"

            # Information (Verspätung / Ausfall)
            info_tag = row.find('td', class_='ris')
            info = ""
            if info_tag:
                info = info_tag.get_text(" ", strip=True)
                # Kürzen für das Display, falls es zu lang wird
                info = info.replace("pünktlich", "").strip()

            fahrplan.append({
                "zeit": zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info
            })
            
        return fahrplan

    except Exception as e:
        print(f"Fehler aufgetreten: {e}")
        return None

# 3. Hauptprogramm
if __name__ == "__main__":
    zug_daten = scrape_bahn_data()
    
    if zug_daten:
        # In daten.json speichern
        with open('daten.json', 'w', encoding='utf-8') as f:
            json.dump(zug_daten, f, ensure_ascii=False, indent=4)
        
        print(f"Erfolgreich aktualisiert am {datetime.now().strftime('%H:%M:%S')}")
        print(f"Anzahl der Züge: {len(zug_daten)}")
    else:
        print("Konnte keine Daten extrahieren.")
