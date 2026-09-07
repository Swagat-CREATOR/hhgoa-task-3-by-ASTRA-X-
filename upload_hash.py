import os
import sys
import json
import hashlib
import chain

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
OD = os.path.join(ROOT, "out")

def canonicalrec(post):
    fields = {
        "title": post.get("title"),
        "link": post.get("link"),
        "source": post.get("source"),
        "image": post.get("image"),
    }
    return json.dumps(fields, sort_keys=True, ensure_ascii=False)

def upload(post):
    record = canonicalrec(post)
    post_hash = hashlib.sha256(record.encode()).hexdigest()
    print("Record:", record)
    print("SHA-256:", post_hash)
    res = chain.submit_memo(post_hash)
    receipt = dict(res)
    receipt["memo"] = post_hash
    receipt["record"] = record
    os.makedirs(OD, exist_ok=True)
    with open(os.path.join(OD, "receipt.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    return receipt

def lp():
    p = os.path.join(OD, "post.json")
    if not os.path.exists(p):
        raise SystemExit("No out/post.json. Run search_post.py first.")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    chosen = data.get("chosen")
    if not chosen:
        raise SystemExit("No chosen post in out/post.json.")
    return chosen

if __name__ == "__main__":
    r = upload(lp())
    print("Backend:", r["backend"], "| network:", r["network"])
    print("Record id:", r["id"])
    print("Explorer:", r["explorer"])
    print("Saved:", os.path.join("out", "receipt.json"))
