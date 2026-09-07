import os
import sys
import hashlib
import face_encode
import search_post
import upload_hash
import chain
import pipeline

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def line(c="="):
    print(c * 64)

def resolve_image(raw):
    s = raw.strip().strip('"').strip("'")
    if not s:
        return None
    cands = [s, os.path.join("faces", s), os.path.join(os.path.expanduser("~"), "Downloads", s)]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None

def ask_image():
    raw = input("Enter the image to search (path or filename, e.g. XYZ.jpeg): ")
    path = resolve_image(raw)
    while path is None:
        if not raw.strip():
            raise SystemExit("No image given. Exiting.")
        print("Could not find that image. I also check faces/ and your Downloads folder.")
        raw = input("Try again: ")
        path = resolve_image(raw)
    return path

def step1(path):
    line()
    print("STEP 1   REVERSE IMAGE SEARCH IN PROGRESS")
    line()
    fr = face_encode.encode_path(path)
    print("Face detected -> 128-d biometric embedding (detector score", round(fr["score"], 4), ")")
    print("Searching the web across Google Lens + Yandex ...")
    print()
    post = search_post.run(path, quiet=True)
    chosen = post.get("chosen")
    if not chosen:
        raise SystemExit("No matching post found. Try another image or set SERPAPI_KEY in .env.")
    sim, matched_src = pipeline.confirm_match(fr["embedding"], post)
    print()
    print("Social media where traces of this photo were found:")
    platforms = post.get("platforms", {})
    order = lambda x: search_post.SOCIAL.index(x) if x in search_post.SOCIAL else 99
    if platforms:
        for p in sorted(platforms, key=order):
            links = platforms[p]
            print("  * " + p + "  (" + str(len(links)) + " post" + ("s" if len(links) != 1 else "") + ")")
            for l in links[:3]:
                print("        " + str(l))
    else:
        print("  (no social-media hits this run; a general web match was used)")
    print()
    print("Total matches:", post["match_count"], "| social matches:", post.get("social_count", 0))
    if sim is not None:
        verdict = "SAME PERSON" if sim >= 0.363 else "uncertain"
        print("Face confirmed on", matched_src, "-> cosine", round(sim, 4), "(" + verdict + ")")
    print()
    print(">> Link chosen to store on the blockchain:")
    print("   " + str(chosen.get("link")))
    print("   source: " + str(chosen.get("source")) + "  |  " + str(chosen.get("title")))
    print()
    return chosen

def step2(chosen):
    line()
    print("STEP 2   BLOCKCHAIN SAVING IN PROCESS")
    line()
    receipt = upload_hash.upload(chosen)
    onchain = chain.read_memo(receipt["id"])
    recomputed = hashlib.sha256(receipt["record"].encode()).hexdigest()
    match = onchain == recomputed
    prog = receipt.get("program")
    if receipt["backend"] == "solana":
        prog = str(prog) + "   (SPL Memo program)"
    print()
    print("Backend            :", receipt["backend"], "(" + receipt["network"] + ")")
    print("Contract / program :", prog)
    print("Wallet             :", receipt.get("wallet"))
    print("Transaction id     :", receipt["id"])
    print("Block / slot       :", receipt.get("block"))
    print("Stored link        :", chosen.get("link"))
    print("On-chain hash      :", onchain)
    print("Recomputed hash    :", recomputed)
    print("On-chain hash true :", "TRUE" if match else "FALSE")
    print("Explorer           :", receipt["explorer"])
    print()
    line()
    if match:
        print("RESULT: VERIFIED  -  data matches the tamper-evident on-chain record.")
    else:
        print("RESULT: MISMATCH  -  data does not match the on-chain record.")
    line()

def main():
    line()
    print("             WELCOME TO HHGOA TASK3")
    line()
    print("Face Identification -> Web/Social Search -> Blockchain Verification")
    backend = os.getenv("CHAIN", "solana").lower()
    if backend == "local":
        print("Chain backend: local simulated chain (offline)")
    else:
        print("Chain backend: Solana devnet  (set CHAIN=local for a no-network demo)")
    print()
    path = ask_image()
    print("Using image:", path)
    print()
    chosen = step1(path)
    step2(chosen)

if __name__ == "__main__":
    main()
