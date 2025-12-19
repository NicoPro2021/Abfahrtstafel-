import requests
import os

ID = os.getenv("DB_CLIENT_ID")
SECRET = os.getenv("DB_CLIENT_SECRET")

def fetch():
    # Wir testen Berlin Hbf (8011160) - der sicherste Testbahnhof
    url = "https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/8011160/251219/10"
    
    headers = {
        "DB-Client-Id": ID,
        "DB-Api-Key": SECRET,
        "Accept": "application/xml"
    }

    print(f"--- SERVER-TEST BERLIN ---")
    r = requests.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Antwort: {r.text[:200]}")

if __name__ == "__main__":
    fetch()
    
