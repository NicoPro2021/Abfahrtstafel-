import requests
import json
import os

def get_db_data():
    # ID für Zerbst/Anhalt
    station_id = "8010405" 
    # Fragt die nächsten 120 Minuten ab
    url = f"https://db.transport.rest/stops/{station_id}/departures?duration=120"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        abfahrten = []
        
        for d in data:
            # Zeit extrahieren
            zeit = d['when'][11:16]
            
            # Info-Logik (Verspätung oder Ausfall)
            info_text = ""
            if d.get('cancelled'):
                info_text = "Zug fällt aus"
            elif d.get('delay') and d['delay'] > 60:
                # Umwandlung von Sekunden in Minuten
                minuten = int(d['delay'] / 60)
                info_text = f"+{minuten} min"
            
            abfahrten.append({
                "zeit": zeit,
                "linie": d['line']['name'],
                "ziel": d['direction'],
                "gleis": d['platform'] if d['platform'] else "--",
                "info": info_text
            })
        return abfahrten
    except Exception as e:
        print(f"Fehler beim Abruf der Daten: {e}")
        return None

# 1. Daten abrufen
live_data = get_db_data()

# 2. Prüfen, ob live_data definiert wurde und Inhalt hat
if live_data is not None:
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(live_data, f, ensure_ascii=False, indent=4)
    print("Daten erfolgreich aktualisiert!")
else:
    print("Fehler: Es konnten keine Daten gespeichert werden.")
