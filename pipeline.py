import os
import sys
import hashlib
import requests
import numpy as np
import cv2
import face_encode
import search_post
import upload_hash
import chain

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) task3-demo/1.0"

def banner(step, text):
    print("\n" + "=" * 62)
    print("STEP " + str(step) + "  " + text)
    print("=" * 62)

def _score_url(input_feat, url, detector, recognizer):
    data = requests.get(url, headers={"User-Agent": UA}, timeout=30).content
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    faces = face_encode.detect_faces(detector, img)
    if not faces:
        return None
    feat, _ = face_encode.encode(recognizer, img, face_encode.largest_face(faces))
    return face_encode.similarity(recognizer, input_feat, feat)

def confirm_match(input_feat, post):
    chosen = post.get("chosen") or {}
    candidates = []
    for key in ("image", "thumbnail"):
        if chosen.get(key):
            candidates.append((chosen.get("source"), chosen.get(key)))
    for m in post.get("matches", []):
        for key in ("image", "thumbnail"):
            if m.get(key):
                candidates.append((m.get("source"), m.get(key)))
    detector, recognizer = face_encode.build()
    seen = set()
    for src, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        try:
            sim = _score_url(input_feat, url, detector, recognizer)
        except Exception:
            sim = None
        if sim is not None:
            return sim, src
    return None, None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("faces", "sample.jpg")

    banner(1, "FACE SCAN  (detect + encode)")
    fr = face_encode.encode_path(path)
    print("Faces:", fr["faces"], "| box:", fr["box"],
          "| score:", round(fr["score"], 4), "| embedding dims:", fr["embedding"].shape[1])

    banner(2, "WEB / SOCIAL SEARCH  (reverse image)")
    post = search_post.run(path)
    chosen = post["chosen"]
    if not chosen:
        raise SystemExit("No matching post found. Try another image or set SERPAPI_KEY.")
    print("Engine:", post["engine"], "| matches:", post["match_count"])
    print("Post title:", chosen.get("title"))
    print("Post link: ", chosen.get("link"))
    print("Source:    ", chosen.get("source"))

    sim, matched_src = confirm_match(fr["embedding"], post)
    if sim is not None:
        verdict = "SAME PERSON" if sim >= 0.363 else "different / uncertain"
        print("Face-match confirmed on:", matched_src)
        print("Face-match vs input (cosine):", round(sim, 4), "->", verdict)
    else:
        print("Face-match check skipped: no candidate image was directly fetchable.")

    banner(3, "BLOCKCHAIN UPLOAD  (memo)")
    receipt = upload_hash.upload(chosen)
    print("Backend:", receipt["backend"], "| network:", receipt["network"])
    print("Record id:", receipt["id"])
    print("Explorer: ", receipt["explorer"])

    banner(4, "BLOCKCHAIN VERIFY  (re-check on-chain record)")
    onchain = chain.read_memo(receipt["id"])
    recomputed = hashlib.sha256(receipt["record"].encode()).hexdigest()
    print("On-chain hash:", onchain)
    print("Recomputed:   ", recomputed)
    print("RESULT:", "VERIFIED" if onchain == recomputed else "MISMATCH")

if __name__ == "__main__":
    main()
