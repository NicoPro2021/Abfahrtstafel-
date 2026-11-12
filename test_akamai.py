import shutil
from playwright.sync_api import sync_playwright

chromium_path = shutil.which("chromium") or shutil.which("chromium-browser")

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=chromium_path,
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    ctx = browser.new_context(locale="de-DE", viewport={"width": 1366, "height": 768})
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    print("1. Lade bahn.de Fahrplansuche...")
    page.goto("https://www.bahn.de/buchung/fahrplan/suche", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(5000)
    page.mouse.move(200, 300)
    page.mouse.click(200, 300)
    page.wait_for_timeout(2000)

    cookies = [c["name"] for c in ctx.cookies()]
    print("Gesetzte Cookies:", cookies)

    test_url = "/web/api/reisebegleitung/wagenreihung/vehicle-sequence?administrationId=80&category=RE&date=2026-11-05&evaNumber=8013389&number=16137&time=2026-11-05T21:13:00.000Z"
    res = page.evaluate("""async (u) => {
        const r = await fetch(u, {
            headers: {
                "Accept": "application/json, text/plain, */*",
                "X-Correlation-ID": crypto.randomUUID() + "_" + crypto.randomUUID()
            },
            credentials: "include"
        });
        return {status: r.status, text: (await r.text()).slice(0, 200)};
    }""", test_url)

    print("Ergebnis aus Seite:", res)
    browser.close()
