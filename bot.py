import requests
from bs4 import BeautifulSoup
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wir nutzen die Standard-Abfahrtstafel, da diese oft stabiler ist
URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?input=Zerbst&boardType=dep&start=yes"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        if response.status_code != 200:
            return [{"zeit": "Error", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []

        # Wir suchen jetzt nach allen Zeilen, die eine Klasse haben, die mit 'train' oder 'dep' zu tun hat
        # Oder einfach alle <tr>, die eine ID mit 'tr_res' haben
        rows = soup.find_all('tr', id=lambda x: x and x.startswith('tr_res_'))

        if not rows:
            # Plan B: Suche nach der Standard-Tabelle, falls IDs fehlen
            rows = soup.find_all('tr', class_=['tpRow', 'depRow'])

        for row in rows:
            zeit_td = row.find('td', class_='time')
            zug_td = row.find('td', class_='train')
            route_td = row.find('td', class_='route')
            
            if zeit_td and zug_td and route_td:
                zeit = zeit_td.get_text(strip=True)
                zug = zug_td.get_text(strip=True).replace(" ", "")
                
                # Verspätung/Info
                info = ""
                ris_tag = row.find('td', class_='ris')
                if ris_tag:
                    info = ris_tag.get_text(strip=True)

                # Ziel extrahieren (das letzte Ziel in der Liste)
                ziel_text = route_td.get_text(" ", strip=True)
                # Oft stehen Zwischenhalte drin, wir wollen nur das Ende
                ziel = ziel_text.split("  ")[-1].strip()

                gleis_td = row.find('td', class_='platform')
                gleis = gleis_td.get_text(strip=True) if gleis_td else "-"

                fahrplan.append({
                    "zeit": zeit,
                    "linie": zug,
                    "ziel": ziel,
                    "gleis": gleis,
                    "info": info
                })

        return fahrplan[:6] if fahrplan else [{"zeit": "Kein", "linie": "ZUG", "ziel": "Gefunden", "gleis": "-", "info": ""}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "Python", "ziel": str(e)[:20], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
