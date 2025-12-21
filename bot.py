import requests
from bs4 import BeautifulSoup
import json

# Die mobile Version der Abfahrtstafel (stabiler für Scraper)
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?L=vs_java3&start=yes&input=Zerbst"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        if response.status_code != 200:
            return [{"zeit": "Error", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []

        # Bei der Java3-Ansicht liegen die Züge meist in <tr> Zeilen mit der Klasse 'list' oder direkt in der Tabelle
        rows = soup.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            # Eine gültige Zeile hat in dieser Ansicht meist Zeit, Zug, Ziel
            if len(cols) >= 3:
                zeit = cols[0].get_text(strip=True)
                # Prüfen, ob im ersten Feld wirklich eine Uhrzeit steht (z.B. 14:05)
                if ":" in zeit and len(zeit) <= 5:
                    zug_linie = cols[1].get_text(strip=True).replace(" ", "")
                    
                    # Das Ziel und eventuelle Infos stehen oft zusammen im dritten Feld
                    ziel_bereich = cols[2]
                    # Eventuelle Verspätungen stehen oft in einem <span class="ris"> oder rot markiert
                    info = ""
                    ris_tag = ziel_bereich.find('span', class_='ris')
                    if ris_tag:
                        info = ris_tag.get_text(strip=True)
                    
                    # Das reine Ziel extrahieren (Text vor dem ersten Zeilenumbruch oder Link)
                    ziel = ziel_bereich.find('a').get_text(strip=True) if ziel_bereich.find('a') else ziel_bereich.get_text(strip=True)
                    
                    # Gleis steht oft in der 4. Spalte, falls vorhanden
                    gleis = ""
                    if len(cols) >= 4:
                        gleis = cols[3].get_text(strip=True)

                    fahrplan.append({
                        "zeit": zeit,
                        "linie": zug_linie,
                        "ziel": ziel,
                        "gleis": gleis,
                        "info": info
                    })

        # Falls der Scraper gar nichts findet, geben wir eine Info aus
        if not fahrplan:
