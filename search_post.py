import os
import re
import sys
import json
import html
import requests
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "out")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) task3-demo/1.0"
SOCIAL = [
    "instagram.com", "twitter.com", "x.com", "facebook.com", "fb.com",
    "linkedin.com", "tiktok.com", "youtube.com", "youtu.be", "threads.net",
    "reddit.com", "pinterest.com", "flickr.com", "vk.com", "tumblr.com",
]

def _serves_image(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200 or len(r.content) < 1000:
            return False
        return r.content[:3] == b"\xff\xd8\xff" or r.content[:4] == b"\x89PNG" or "image" in r.headers.get("content-type", "")
    except Exception:
        return False

def upload_image(path):
    with open(path, "rb") as f:
        data = f.read()
    name = os.path.basename(path)

    def uguu():
        r = requests.post("https://uguu.se/upload.php", files={"files[]": (name, data)}, timeout=40)
        return r.json()["files"][0]["url"]

    def tmpfiles():
        r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": (name, data)}, timeout=40)
        return r.json()["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)

    def catbox():
        r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"},
                          files={"fileToUpload": (name, data)}, timeout=40)
        return r.text.strip()

    for kind, fn in [("uguu", uguu), ("tmpfiles", tmpfiles), ("catbox", catbox)]:
        try:
            link = fn()
            if link.startswith("http") and _serves_image(link):
                print("Hosted query image at:", link, "(" + kind + ")")
                return link
            print("Host", kind, "did not serve a valid image, trying next.")
        except Exception as e:
            print("Upload via", kind, "failed:", e)
    raise SystemExit("Could not host the query image on any provider.")

def is_social(u):
    u = (u or "").lower()
    return any(s in u for s in SOCIAL)

def search_serpapi(image_url, key):
    params = {"engine": "google_lens", "url": image_url, "api_key": key, "hl": "en"}
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=90)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("visual_matches", []):
        results.append({
            "title": m.get("title"),
            "link": m.get("link"),
            "source": m.get("source"),
            "image": m.get("image") or m.get("thumbnail"),
            "thumbnail": m.get("thumbnail"),
        })
    return results

def search_yandex(image_url):
    r = requests.get("https://yandex.com/images/search",
                     params={"rpt": "imageview", "url": image_url, "cbir_page": "sites"},
                     headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}, timeout=90)
    raw = r.text
    if "showcaptcha" in raw.lower() or "smartcaptcha" in raw.lower():
        print("Yandex returned a CAPTCHA. Add SERPAPI_KEY to .env for reliable search.")
        return []
    results = []
    seen = set()
    for chunk in raw.split('class="CbirSites-Item"')[1:]:
        mt = re.search(r'CbirSites-ItemTitle"><a href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
        if not mt:
            continue
        link = html.unescape(mt.group(1))
        title = html.unescape(re.sub(r"<[^>]+>", "", mt.group(2))).strip()
        mi = re.search(r'CbirSites-ItemThumb"[^>]*><a href="([^"]+)"', chunk)
        image = html.unescape(mi.group(1)) if mi else None
        host = link.split("/")[2] if "//" in link else link
        if link in seen:
            continue
        seen.add(link)
        results.append({"title": title, "link": link, "source": host, "image": image, "thumbnail": image})
    return results

def choose(results):
    if not results:
        return None
    social = [r for r in results if is_social(r.get("link")) or is_social(r.get("source"))]
    return social[0] if social else results[0]

def run(image_path):
    key = os.getenv("SERPAPI_KEY", "").strip()
    image_url = upload_image(image_path)
    engine = "serpapi" if key else "yandex"
    print("Search engine:", engine)
    results = search_serpapi(image_url, key) if key else search_yandex(image_url)
    if not results and key:
        print("SerpAPI found nothing; falling back to Yandex.")
        engine = "yandex"
        results = search_yandex(image_url)
    post = {
        "engine": engine,
        "query_image_url": image_url,
        "match_count": len(results),
        "matches": results[:10],
        "chosen": choose(results),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "post.json"), "w", encoding="utf-8") as f:
        json.dump(post, f, indent=2, ensure_ascii=False)
    return post

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("faces", "sample.jpg")
    p = run(path)
    c = p["chosen"]
    if not c:
        print("No matching post found.")
        raise SystemExit(0)
    print("Matches found:", p["match_count"])
    print("Chosen post title:", c.get("title"))
    print("Chosen post link:", c.get("link"))
    print("Source:", c.get("source"))
    print("Matched image:", c.get("image"))
    print("Saved:", os.path.join("out", "post.json"))
