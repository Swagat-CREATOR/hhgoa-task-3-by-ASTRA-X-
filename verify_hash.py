import os
import sys
import json
import hashlib
import chain

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")



def load_receipt():
    p = os.path.join(OUT_DIR, "receipt.json")
    if not os.path.exists(p):
        raise SystemExit("No out/receipt.json. Run upload_hash.py first.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def main():
    receipt = load_receipt()
    record = receipt["record"]
    if "--tamper" in sys.argv:
        record = record + "TAMPERED"
        print("Tamper mode: recomputing from a MODIFIED record")
    recomputed = hashlib.sha256(record.encode()).hexdigest()
    onchain = chain.read_memo(receipt["id"])
    print("Backend:           ", receipt["backend"], "|", receipt["network"])
    print("Record id:         ", receipt["id"])
    print("On-chain memo hash:", onchain)
    print("Recomputed hash:   ", recomputed)
    if onchain is None:
        raise SystemExit("Could not read memo from chain.")
    if onchain == recomputed:
        print("RESULT: VERIFIED - record matches the on-chain tamper-evident record.")
    else:
        print("RESULT: MISMATCH - data does not match the on-chain record (tamper detected).")

if __name__ == "__main__":
    main()
