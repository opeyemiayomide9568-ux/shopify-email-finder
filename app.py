from flask import Flask, render_template, request, jsonify, send_file
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import requests, re, io, csv, time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
HEADERS = {"User-Agent": "ShopifyEmailFinder/1.0 (public business contact lookup)"}
TIMEOUT = 12
MAX_PAGES_PER_STORE = 5
DELAY_BETWEEN_STORES = 1.0

def normalize_url(raw):
    raw = raw.strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    p = urlparse(raw)
    if not p.netloc or p.scheme not in ("http", "https"):
        return None
    return f"{p.scheme}://{p.netloc}"

def allowed_by_robots(base, url):
    try:
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        # If robots.txt cannot be checked, skip crawling rather than assume permission.
        return False

def scan_store(raw_url):
    base = normalize_url(raw_url)
    if not base:
        return {"store": raw_url, "emails": [], "status": "Invalid URL"}
    candidates = [base, urljoin(base, "/pages/contact"), urljoin(base, "/pages/about"),
                  urljoin(base, "/policies/contact-information"),
                  urljoin(base, "/")]
    seen_pages, found = set(), set()
    checked = 0
    for page in candidates:
        if page in seen_pages or checked >= MAX_PAGES_PER_STORE:
            continue
        seen_pages.add(page)
        if not allowed_by_robots(base, page):
            continue
        try:
            response = requests.get(page, headers=HEADERS, timeout=TIMEOUT,
                                    allow_redirects=True)
            if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
                continue
            checked += 1
            soup = BeautifulSoup(response.text[:2_000_000], "html.parser")
            for a in soup.select('a[href^="mailto:"]'):
                found.update(EMAIL_RE.findall(a.get("href", "")))
            text = soup.get_text(" ", strip=True)
            found.update(EMAIL_RE.findall(text))
            # Also inspect visible HTML attributes, but not scripts or hidden source bundles.
            for el in soup.select("[aria-label], [title]"):
                found.update(EMAIL_RE.findall(el.get("aria-label", "") + " " + el.get("title", "")))
        except requests.RequestException:
            continue
    return {"store": base, "emails": sorted(found), "status": f"{checked} public page(s) checked" if checked else "No pages checked (robots.txt may disallow crawling)"}

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/scan")
def scan():
    data = request.get_json(silent=True) or {}
    urls = data.get("urls", [])
    urls = [u.strip() for u in urls if isinstance(u, str) and u.strip()]
    urls = list(dict.fromkeys(urls))[:25]
    if not urls:
        return jsonify({"error": "Add at least one store URL."}), 400
    results = []
    # Sequential crawling and a delay keep requests modest and avoid aggressive scraping.
    for url in urls:
        results.append(scan_store(url))
        time.sleep(DELAY_BETWEEN_STORES)
    return jsonify({"results": results})

@app.post("/api/export")
def export():
    data = request.get_json(silent=True) or {}
    rows = data.get("results", [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Store URL", "Public email", "Scan status"])
    for row in rows:
        emails = row.get("emails") or [""]
        for email in emails:
            writer.writerow([row.get("store", ""), email, row.get("status", "")])
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True,
                     download_name="shopify-public-contacts.csv")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
