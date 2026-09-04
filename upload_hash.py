import os
import sys
import json
import hashlib
import chain

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "out")

def canonical_record(post):
    fields = {
        "title": post.get("title"),
        "link": post.get("link"),
        "source": post.get("source"),
        "image": post.get("image"),
    }
    return json.dumps(fields, sort_keys=True, ensure_ascii=False)

def upload(post):
    record = canonical_record(post)
    post_hash = hashlib.sha256(record.encode()).hexdigest()
    print("Record:", record)
    print("SHA-256:", post_hash)
    res = chain.submit_memo(post_hash)
    receipt = dict(res)
    receipt["memo"] = post_hash
    receipt["record"] = record
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "receipt.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    return receipt

def load_post():
    p = os.path.join(OUT_DIR, "post.json")
    if not os.path.exists(p):
        raise SystemExit("No out/post.json. Run search_post.py first.")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    chosen = data.get("chosen")
    if not chosen:
        raise SystemExit("No chosen post in out/post.json.")
    return chosen

if __name__ == "__main__":
    r = upload(load_post())
    print("Backend:", r["backend"], "| network:", r["network"])
    print("Record id:", r["id"])
    print("Explorer:", r["explorer"])
    print("Saved:", os.path.join("out", "receipt.json"))
