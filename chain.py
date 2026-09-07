import os
import re
import time
import json
import base64
import hashlib
import requests

BACKEND = os.getenv("CHAIN", "solana").lower()
RPC = os.getenv("SOLANA_RPC", "https://api.devnet.solana.com")
CLUSTER = os.getenv("SOLANA_CLUSTER", "devnet")
MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "out")
LEDGER = os.path.join(OUT_DIR, "localchain.json")
WALLET_FILE = os.path.join(ROOT, "wallet.json")

def _rpc(method, params):
    r = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(method + " error: " + str(data["error"]))
    return data["result"]

def _load_wallet():
    from solders.keypair import Keypair
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE) as f:
            return Keypair.from_bytes(bytes(json.load(f)))
    kp = Keypair()
    with open(WALLET_FILE, "w") as f:
        json.dump(list(bytes(kp)), f)
    return kp

def _confirm(signature, timeout=60):
    for _ in range(timeout):
        st = _rpc("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])["value"][0]
        if st and st.get("err"):
            raise RuntimeError("Transaction failed: " + str(st["err"]))
        if st and st.get("confirmationStatus") in ("confirmed", "finalized"):
            return True
        time.sleep(1)
    return False

def _ensure_funds(payer):
    bal = _rpc("getBalance", [str(payer.pubkey())])["value"]
    if bal >= 1_000_000:
        return bal
    for attempt in range(1, 7):
        print("Requesting devnet airdrop (attempt " + str(attempt) + ")...")
        try:
            sig = _rpc("requestAirdrop", [str(payer.pubkey()), 1_000_000_000])
            _confirm(sig)
        except Exception as e:
            print("Airdrop request failed:", e)
        for _ in range(15):
            bal = _rpc("getBalance", [str(payer.pubkey())])["value"]
            if bal >= 1_000_000:
                return bal
            time.sleep(1)
        time.sleep(3)
    return bal

def _solana_submit(text):
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction
    from solders.message import Message
    from solders.transaction import Transaction
    from solders.hash import Hash
    payer = _load_wallet()
    print("Wallet:", payer.pubkey())
    bal = _ensure_funds(payer)
    print("Balance (lamports):", bal)
    if bal < 5000:
        raise SystemExit("Wallet unfunded. Fund " + str(payer.pubkey()) + " at https://faucet.solana.com, or run with CHAIN=local.")
    ix = Instruction(Pubkey.from_string(MEMO_PROGRAM), text.encode(), [])
    last_err = None
    for attempt in range(1, 5):
        bh = Hash.from_string(_rpc("getLatestBlockhash", [{"commitment": "finalized"}])["value"]["blockhash"])
        msg = Message.new_with_blockhash([ix], payer.pubkey(), bh)
        tx = Transaction([payer], msg, bh)
        try:
            sig = _rpc("sendTransaction", [base64.b64encode(bytes(tx)).decode(),
                                           {"encoding": "base64", "preflightCommitment": "finalized"}])
        except RuntimeError as e:
            last_err = e
            if "Blockhash" in str(e) and attempt < 4:
                print("Blockhash expired, retrying with a fresh one (attempt " + str(attempt) + ")...")
                time.sleep(1)
                continue
            raise
        if _confirm(sig):
            return {
                "backend": "solana",
                "network": CLUSTER,
                "id": sig,
                "wallet": str(payer.pubkey()),
                "explorer": "https://explorer.solana.com/tx/" + sig + "?cluster=" + CLUSTER,
            }
        print("Transaction not confirmed in time, retrying (attempt " + str(attempt) + ")...")
    raise SystemExit("Solana submit failed after retries: " + str(last_err))

def _solana_read(record_id):
    tx = _rpc("getTransaction", [record_id, {"encoding": "json", "maxSupportedTransactionVersion": 0, "commitment": "confirmed"}])
    if tx is None:
        raise SystemExit("Transaction not found on-chain yet.")
    logs = (tx.get("meta") or {}).get("logMessages") or []
    for line in logs:
        m = re.search(r'Memo \(len \d+\): "(.*)"', line)
        if m:
            return m.group(1)
    return None

def _block_hash(index, memo, prev):
    return hashlib.sha256((str(index) + memo + prev).encode()).hexdigest()

def _local_submit(text):
    os.makedirs(OUT_DIR, exist_ok=True)
    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    prev = ledger[-1]["block_hash"] if ledger else "0" * 64
    index = len(ledger)
    block = {"index": index, "memo": text, "prev": prev}
    block["block_hash"] = _block_hash(index, text, prev)
    ledger.append(block)
    json.dump(ledger, open(LEDGER, "w"), indent=2)
    return {"backend": "local", "network": "local", "id": str(index), "wallet": "local", "explorer": LEDGER}

def _local_read(record_id):
    if not os.path.exists(LEDGER):
        return None
    ledger = json.load(open(LEDGER))
    for i, b in enumerate(ledger):
        if b["block_hash"] != _block_hash(b["index"], b["memo"], b["prev"]):
            raise SystemExit("Local chain corrupted at block " + str(i))
        if i > 0 and b["prev"] != ledger[i - 1]["block_hash"]:
            raise SystemExit("Local chain broken link at block " + str(i))
    idx = int(record_id)
    return ledger[idx]["memo"] if 0 <= idx < len(ledger) else None

def submit_memo(text):
    return _local_submit(text) if BACKEND == "local" else _solana_submit(text)

def read_memo(record_id):
    return _local_read(record_id) if BACKEND == "local" else _solana_read(record_id)
