import requests
from bs4 import BeautifulSoup
import json
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir nehmen die einfache Abfahrts-Suche
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?input=Zerbst&boardType=dep&start=yes"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        if response.status_code != 200:
            return [{"zeit": "Err", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []

        # Wir suchen nach JEDER Tabellenzeile
        rows = soup.find_all('tr')

        for row in rows:
            text = row.get_text(" ", strip=True)
            # Regex: Sucht nach Uhrzeiten wie 14:05 oder 09:12
            zeit_match = re.search(r'(\d{1,2}:\d{2})', text)
            
            if zeit_match:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    zeit = zeit_match.group(1)
                    
                    # Zugname (z.B. RE 13 oder RB 42)
                    zug = ""
                    train_td = row.find('td', class_='train')
                    if train_td:
                        zug = train_td.get_text(strip=True).replace(" ", "")
                    else:
                        zug = cols[1].get_text(strip=True).replace(" ", "")

                    # Ziel
                    ziel = ""
                    route_td = row.find('td', class_='route')
                    if route_td:
                        ziel = route_td.get_text(" ", strip=True).split("  ")[-1].strip()
                    else:
                        ziel = cols[2].get_text(strip=True).split("  ")[-1].strip()

                    # Infos (Verspätung)
                    info = ""
                    ris_tag = row.find('td', class_='ris')
                    if ris_tag:
                        info = ris_tag.get_text(strip=True)

                    # Gleis
                    gleis = ""
                    platform_td = row.find('td', class_='platform')
                    if platform_td:
                        gleis = platform_td.get_text(strip=True)

                    # Nur hinzufügen, wenn es kein Kopfzeilen-Müll ist
                    if len(zug) > 1 and "Ankunft" not in ziel:
                        fahrplan.append({
                            "zeit": zeit,
                            "linie": zug,
                            "ziel": ziel[:20], # Kürzen für das Display
                            "gleis": gleis,
                            "info": info
                        })

        # Duplikate entfernen (manchmal listet die Bahn Züge doppelt)
        seen = set()
        unique_fahrplan = []
        for f in fahrplan:
            identifier = f"{f['zeit']}{f['linie']}"
            if identifier not in seen:
                unique_fahrplan.append(f)
                seen.add(identifier)

        return unique_fahrplan[:6] if unique_fahrplan else [{"zeit": "Kein", "linie": "ZUG", "ziel": "Gefunden", "gleis": "", "info": ""}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "Py", "ziel": str(e)[:15], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
