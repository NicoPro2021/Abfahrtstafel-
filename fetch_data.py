import requests
import os

# Holen der Secrets
CLIENT_ID = os.getenv("DB_CLIENT_ID")
CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")

# Test-URL für den Bahnhof Zerbst
# Wir nutzen 'plan', da dies die stabilste Methode für den ersten Test ist
url = "https://apis.deutschebahn.com/db-api-marketplace/v1/timetables/plan/8010386/251218/22"

headers = {
    "DB-Client-Id": CLIENT_ID,
    "DB-Api-Key": CLIENT_SECRET,
    "accept": "application/json"
}

print(f"Teste Verbindung mit ID: {CLIENT_ID[:5]}***")

try:
    response = requests.get(url, headers=headers)
    print(f"Status-Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Erfolg! Die DB-API hat geantwortet.")
        print("Daten-Vorschau:", response.text[:200])
    elif response.status_code == 401:
        print("Fehler 401: Deine API-Keys (Secrets) sind falsch oder noch nicht aktiv.")
    elif response.status_code == 404:
        print("Fehler 404: Bahnhof-ID oder Zeit nicht gefunden.")
    else:
        print(f"Anderer Fehler: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Verbindungsfehler: {e}")
    
