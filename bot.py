import json
from datetime import datetime, timedelta, timezone
from pyhafas import HafasClient
from pyhafas.profile import DBProfile

def hole_daten():
    # Deutsche Zeit für den Update-Stempel
    u_zeit = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%H:%M")
    client = HafasClient(DBProfile())
    
    # Station ID für Zerbst/Anhalt: 8010405
    # Station ID für Berlin-Wannsee: 8010358
    station_id = "8010405" 

    try:
        # Abfrage der nächsten 120 Minuten
        departures = client.departures(
            station=station_id,
            date=datetime.now(),
            duration=120
        )
        
        fahrplan = []
        for dep in departures:
            # Planmäßige Zeit
            soll_zeit = dep.dateTime.strftime("%H:%M")
            
            # Tatsächliche Zeit berechnen (Soll + Verspätung)
            ist_zeit = soll_zeit
            delay_min = 0
            if dep.delay:
                delay_min = int(dep.delay.total_seconds() / 60)
                ist_zeit = (dep.dateTime + dep.delay).strftime("%H:%M")

            # Linie (z.B. RE13) und Ziel
            linie = dep.name.replace(" ", "")
            ziel = dep.direction[:20] if dep.direction else "Ziel unbekannt"
            gleis = dep.platform if dep.platform else "-"

            # Verspätungsgründe (Remarks) sammeln
            hinweise = []
            if dep.remarks:
                for rm in dep.remarks:
                    if hasattr(rm, 'text') and rm.text:
                        txt = rm.text.strip()
                        # Unnötiges filtern
                        if "Fahrrad" not in txt and "WLAN" not in txt and txt not in hinweise:
                            hinweise.append(txt)

            grund = " | ".join(hinweise)
            
            # Info-Text Logik
            if dep.cancelled:
                info_text = "FÄLLT AUS!"
            elif delay_min > 0:
                # Zeigt z.B. "+5 Min: Signalstörung"
                info_text = f"+{delay_min} Min: {grund}" if grund else f"+{delay_min} Min"
            else:
                info_text = grund # Falls pünktlich, aber Bauinfos da sind

            fahrplan.append({
                "zeit": soll_zeit,
                "echte_zeit": ist_zeit,
                "linie": linie,
                "ziel": ziel,
                "gleis": gleis,
                "info": info_text,
                "update": u_zeit
            })

        # Nach tatsächlicher Abfahrt sortieren
        fahrplan.sort(key=lambda x: x['echte_zeit'])
        return fahrplan[:15]

    except Exception as e:
        return [{"zeit": "Err", "linie": "HAFAS", "ziel": "Error", "gleis": "-", "info": str(e)[:15], "update": u_zeit}]

if __name__ == "__main__":
    daten = hole_daten()
    with open('daten.json', 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
