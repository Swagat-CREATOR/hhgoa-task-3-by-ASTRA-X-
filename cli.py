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

os.system("")

def paint(text, code):
    return "\033[" + code + "m" + str(text) + "\033[0m"

def link(url):
    return "\033[4;94m" + str(url) + "\033[0m"

def verdict(flag, good, bad):
    return paint(good, "1;92") if flag else paint(bad, "1;91")

def line(c="="):
    print(paint(c * 64, "1;90"))

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
    print(paint("STEP 1   REVERSE IMAGE SEARCH IN PROGRESS", "1;96"))
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
                print("        " + link(l))
    else:
        print("  (no social-media hits this run; a general web match was used)")
    print()
    print("Total matches:", post["match_count"], "| social matches:", post.get("social_count", 0))
    if sim is not None:
        same = sim >= 0.363
        tag = verdict(same, "SAME PERSON", "uncertain")
        print("Face confirmed on", matched_src, "-> cosine", round(sim, 4), "(" + tag + ")")
    print()
    print(paint(">> Link chosen to store on the blockchain:", "1;93"))
    print("   " + link(chosen.get("link")))
    print("   source: " + str(chosen.get("source")) + "  |  " + str(chosen.get("title")))
    print()
    return chosen

def step2(chosen):
    line()
    print(paint("STEP 2   BLOCKCHAIN SAVING IN PROCESS", "1;96"))
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
    print("Transaction id     :", paint(receipt["id"], "93"))
    print("Block / slot       :", receipt.get("block"))
    print("Stored link        :", link(chosen.get("link")))
    print("On-chain hash      :", paint(onchain, "95"))
    print("Recomputed hash    :", paint(recomputed, "95"))
    print("On-chain hash true :", verdict(match, "TRUE", "FALSE"))
    print("Explorer           :", link(receipt["explorer"]))
    print()
    line()
    if match:
        print(verdict(True, "RESULT: VERIFIED  -  data matches the tamper-evident on-chain record.", ""))
    else:
        print(verdict(False, "", "RESULT: MISMATCH  -  data does not match the on-chain record."))
    line()
    return receipt

def step3(receipt):
    line()
    print(paint("STEP 3   TAMPER CHECK (is the on-chain record really tamper-evident?)", "1;96"))
    line()
    print("Re-reading the record from the chain, then altering the local copy")
    print("the way an attacker would, and re-hashing it ...")
    onchain = chain.read_memo(receipt["id"])
    tampered = receipt["record"] + "TAMPERED"
    recomputed = hashlib.sha256(tampered.encode()).hexdigest()
    match = onchain == recomputed
    print()
    print("On-chain hash          :", paint(onchain, "95"))
    print("Hash of TAMPERED record:", paint(recomputed, "95"))
    print("Hashes match           :", verdict(match, "TRUE", "FALSE"))
    print()
    line()
    if match:
        print(verdict(True, "RESULT: UNEXPECTED  -  tampered data matched (this should never happen).", ""))
    else:
        print(paint("RESULT: TAMPER DETECTED  -  altered data does NOT match the on-chain record.", "1;92"))
    line()

def main():
    line()
    print(paint("             WELCOME TO HHGOA TASK3", "1;95"))
    line()
    print(paint("Face Identification -> Web/Social Search -> Blockchain Verification", "1;97"))
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
    receipt = step2(chosen)
    step3(receipt)

if __name__ == "__main__":
    main()
