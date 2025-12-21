import requests
from bs4 import BeautifulSoup
import json
import urllib3

# Deaktiviert die nervigen SSL-Warnungen im Log, da wir das Zertifikat ignorieren
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Die mobile Version der Abfahrtstafel (stabiler für Scraper)
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?L=vs_java3&start=yes&input=Zerbst"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # verify=False ist die Lösung für deinen SSL-Fehler
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Error", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []

        # In der Java3-Ansicht sind die Züge in Tabellenzeilen (tr)
        rows = soup.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            # Eine gültige Zeile hat mindestens Zeit, Zugname und Ziel
            if len(cols) >= 3:
                zeit = cols[0].get_text(strip=True)
                
                # Wir prüfen, ob im ersten Feld wirklich eine Uhrzeit steht (z.B. 14:05)
                if ":" in zeit and len(zeit) <= 5:
                    zug_linie = cols[1].get_text(strip=True).replace(" ", "")
                    
                    ziel_bereich = cols[2]
                    # Suche nach Verspätungsinfos (oft in 'ris' Klasse)
                    info = ""
                    ris_tag = ziel_bereich.find('span', class_='ris')
                    if ris_tag:
                        info = ris_tag.get_text(strip=True)
                    
                    # Das Ziel extrahieren
                    ziel = ziel_bereich.find('a').get_text(strip=True) if ziel
