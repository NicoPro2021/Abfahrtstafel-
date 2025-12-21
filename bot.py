import requests
from bs4 import BeautifulSoup
import json
import urllib3

# Deaktiviert SSL-Warnungen
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://reiseauskunft.bahn.de/bin/bhftafel.exe/dn?L=vs_java3&start=yes&input=Zerbst"

def hole_daten():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # SSL-Prüfung wird mit verify=False umgangen
        response = requests.get(URL, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            return [{"zeit": "Error", "linie": "HTTP", "ziel": str(response.status_code), "gleis": "", "info": ""}]

        soup = BeautifulSoup(response.text, 'html.parser')
        fahrplan = []

        # Suche alle Tabellenzeilen
        rows = soup.find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                zeit = cols[0].get_text(strip=True)
                
                # Check ob es eine Uhrzeit ist
                if ":" in zeit and len(zeit) <= 5:
                    zug_linie = cols[1].get_text(strip=True).replace(" ", "")
                    
                    ziel_bereich = cols[2]
                    # Verspätung suchen
                    info = ""
                    ris_tag = ziel_bereich.find('span', class_='ris')
                    if ris_tag:
                        info = ris_tag.get_text(strip=True)
                    
                    # Ziel extrahieren (Hier war der Syntaxfehler)
                    if ziel_bereich.find('a'):
                        ziel = ziel_bereich.find('a').get_text(strip=True)
                    else:
                        ziel = ziel_bereich.get_text(strip=True)
                    
                    # Info aus dem Zieltext entfernen
                    ziel = ziel.replace(info, "").strip()

                    gleis = cols[3].get_text(strip=True) if len(cols) >= 4 else ""

                    fahrplan.append({
                        "zeit": zeit,
                        "linie": zug_linie,
                        "ziel": ziel,
                        "gleis": gleis,
                        "info": info
                    })

        return fahrplan[:6] if fahrplan else [{"zeit": "00:00", "linie": "INFO", "ziel": "Keine Daten", "gleis": "-", "info": ""}]

    except Exception as e:
        return [{"zeit": "Error", "linie": "Python", "ziel": str(e)[:20], "gleis": "", "info": ""}]

if __name__ == "__main__":
    aktuelle_daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(aktuelle_daten, f, ensure_ascii=False, indent=4)
    print("Bot: daten.json erfolgreich geschrieben.")
