import requests
import json
import os
from datetime import datetime, timedelta

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")

def fetch():
    # Wir nutzen die stabilste Basis-URL der Timetables API
    base_url = "https://apis.deutschebahn.com/db-api-marketplace/v1/timetables"
    
    # Zeit berechnen (UTC+1)
    now = datetime.utcnow() + timedelta(hours=1)
    datum = now.strftime("%y%m%d")
    stunde = now.strftime("%H")
    
    # Test-Bahnhöfe: Zerbst und Berlin
    stations = [("8010386", "Zerbst"), ("8011160", "Berlin Hbf")]
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "Accept": "application/xml" # Wir probieren XML, da die API das nativ liefert
    }

    print(f"--- FINALE DIAGNOSE ---")
    
    for eva, name in stations:
        url = f"{base_url}/plan/{eva}/{datum}/{stunde}"
        print(f"Abfrage {name}: {url}")
        
        try:
            r = requests.get(url, headers=headers)
            print(f"Status: {r.status_code}")
            
            if r.status_code == 200:
                print(f"!!! ERFOLG BEI {name} !!!")
                # Da die API XML liefert, speichern wir es erst mal roh
                with open('daten.json', 'w', encoding='utf-8') as f:
                    f.write(r.text) 
                return # Beenden bei Erfolg
            else:
                print(f"Antwort: {r.text[:100]}") # Zeige den Anfang der Fehlermeldung
        except Exception as e:
            print(f"Fehler: {str(e)}")

if __name__ == "__main__":
    fetch()
    
