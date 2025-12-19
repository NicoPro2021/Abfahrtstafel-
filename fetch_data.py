import requests
import json
import os
from datetime import datetime, timedelta

# Nutze die neuen Keys aus deinem Screenshot
ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")

def fetch():
    # Aktuelle deutsche Zeit (UTC+1)
    now = datetime.utcnow() + timedelta(hours=1)
    d = now.strftime("%y%m%d")
    h = now.strftime("%H")
    
    # Wir testen Zerbst
    eva = "8010386"
    url = f"https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/{eva}/{d}/{h}"
    
    # Manche DB-APIs verlangen das Secret als 'DB-Api-Key' 
    # und andere als 'X-DB-Api-Key'. Wir senden sicherheitshalber beide.
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "X-DB-Client-Id": ID,
        "X-DB-Api-Key": SECRET,
        "Accept": "application/xml"
    }

    print(f"--- FINALE PRÜFUNG ---")
    print(f"URL: {url}")
    
    r = requests.get(url, headers=headers)
    print(f"Status-Code: {r.status_code}")
    
    if r.status_code == 200:
        print("ERFOLG! Daten empfangen.")
        with open('daten.json', 'w', encoding='utf-8') as f:
            # Wir speichern erst mal das XML, um zu sehen was drin ist
            f.write(r.text)
    else:
        print(f"Fehlermeldung: {r.text[:200]}")
        print("Hinweis: Wenn das immer noch 404 liefert, ist das Abo im Portal")
        print("zwar optisch aktiv, aber technisch nicht auf die Keys geroutet.")

if __name__ == "__main__":
    fetch()
    
