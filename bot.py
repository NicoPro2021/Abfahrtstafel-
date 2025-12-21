import requests
from bs4 import BeautifulSoup
import json

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
        rows = soup.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                zeit = cols[0].get_text(strip=True)
                if ":" in zeit and len(zeit) <= 5:
                    zug = cols[1].get_text(strip=True).replace(" ", "")
                    ziel_td = cols[2]
                    
                    # Info (Verspätung) suchen
                    info = ""
                    ris = ziel_td.find('span', class_='ris')
                    if ris:
                        info = ris.get_text(strip=True)
                    
                    # Ziel säubern
                    ziel = ziel_td.find('a').get_text(strip=True) if ziel_td.find('a') else ziel_td.get_text(strip=True)
                    ziel = ziel.replace(info, "").strip() # Info aus Zieltext entfernen

                    gleis = cols[3].get_text(strip=True) if len(cols) >= 4 else ""

                    fahrplan.append({
                        "zeit": zeit,
                        "linie": zug,
                        "ziel": ziel,
                        "gleis": gleis,
                        "info": info
                    })
        return fahrplan[:6] if fahrplan else [{"zeit": "00:00", "linie": "INFO", "ziel": "Keine Züge", "gleis": "", "info": ""}]
    except Exception as e:
        return [{"zeit": "Error", "linie": "Python", "ziel": str(e), "gleis": "", "info": ""}]

if __name__ == "__main__":
    data = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
