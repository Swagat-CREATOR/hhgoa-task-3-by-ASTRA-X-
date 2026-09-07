# Face Identification → Web Search → Blockchain Verification

An end-to-end pipeline that takes a **face scan**, finds a **real matching post on the web / social media**, then writes a tamper-evident **fingerprint of that discovery to a blockchain** and re-verifies it against the on-chain record.

```
face image  ──▶  detect + encode face   (OpenCV YuNet + SFace, 128-d embedding)
            ──▶  reverse image search    (SerpAPI Google Lens, Yandex fallback)
            ──▶  confirm identity         (re-encode match, cosine similarity vs input)
            ──▶  SHA-256 the found post   (canonical title|link|source|image record)
            ──▶  write hash to chain      (Solana devnet SPL Memo, or local sim chain)
            ──▶  re-read + re-verify       (on-chain hash == recomputed hash)
```

## What each stage does

1. **Face identification** — `face_encode.py` detects the largest face with OpenCV **YuNet** and encodes it to a 128-dimension embedding with **SFace**. Models auto-download on first run.
2. **Web / social search** — `search_post.py` hosts the query image on a temporary public host, then runs a **genuine reverse image search across both engines at once** (SerpAPI Google Lens **and** keyless Yandex), merges and dedupes the hits, and picks a matching post **ranked by social platform priority** (Instagram → Facebook → X → LinkedIn → TikTok → YouTube → …). Keeping the top 40 matches means social posts that rank below stock-photo sites still survive to the pick.
3. **Identity confirmation** — the matched image is re-encoded and compared to the input embedding via SFace cosine similarity, so a hit is a *face* match, not just a lookalike thumbnail. It walks every candidate image (chosen post first, then the rest of the matches) until one is directly fetchable, so the match still confirms even when the top pick sits behind a crawler-only host.
4. **Blockchain verification** — `upload_hash.py` builds a canonical record of the post, hashes it with SHA-256, and writes the hash to chain via `chain.py`. `verify_hash.py` reads the record back off-chain and re-hashes to prove it is unchanged. `--tamper` demonstrates detection of any modification.

## Blockchain used

- **Primary: Solana devnet** via the **SPL Memo program** (`MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr`). The SHA-256 of the post is stored in a memo instruction; the transaction signature is the receipt, viewable on Solana Explorer. Built with `solders` over raw JSON-RPC (no wrapper lock-in).
- **Fallback: local simulated chain** (`CHAIN=local`) — an append-only, hash-linked ledger (`out/localchain.json`) where each block commits to the previous block's hash. Fully offline, no funding, and tamper-evident by the same re-verification. Handy when the public devnet faucet is rate-limited.

> **Live proof (Solana devnet).** A real memo transaction anchoring the SHA-256 of a discovered Instagram post:
> [`2yfT3S4YfUSbBVk1ezjapM2RipL9U9gh87aJCxPZdh58vwPFioaCNia3L1Bs6UwnAYRPFNJ4QvRRs9ZeTmPux2QK`](https://explorer.solana.com/tx/2yfT3S4YfUSbBVk1ezjapM2RipL9U9gh87aJCxPZdh58vwPFioaCNia3L1Bs6UwnAYRPFNJ4QvRRs9ZeTmPux2QK?cluster=devnet)
> — open it on Solana Explorer to see the on-chain memo hash `fa860da9…58c6`. `verify_hash.py` reads it back and re-hashes to `VERIFIED`; `--tamper` flips it to `MISMATCH`.
>
> When the public faucet is throttled and no wallet funding is available, `CHAIN=local` runs the identical hash → write → re-verify → tamper-detect flow with zero external dependencies.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env
```

Add a free SerpAPI key (recommended for reliable search — serpapi.com):

```bash
SERPAPI_KEY=your_key_here
```

## Run the interactive CLI (recommended)

```bash
.venv/Scripts/python cli.py
```

It prints `WELCOME TO HHGOA TASK3`, asks for an image (a path, or just a filename it will look up in `faces/` and your Downloads folder), then runs **Step 1 — reverse image search** (listing every social platform the face was found on and the link it will anchor) and **Step 2 — blockchain saving** (printing the program address, transaction id, block/slot, on-chain hash, and whether it re-verifies `TRUE`). Set `CHAIN=local` first for the offline demo.

## Run the full pipeline (non-interactive)

```bash
.venv/Scripts/python pipeline.py faces/sample.jpg
```

Run it against the guaranteed local chain (no faucet needed):

```bash
CHAIN=local .venv/Scripts/python pipeline.py faces/sample.jpg
```

## Run each stage on its own

```bash
.venv/Scripts/python face_encode.py faces/sample.jpg
.venv/Scripts/python search_post.py faces/sample.jpg
.venv/Scripts/python upload_hash.py
.venv/Scripts/python verify_hash.py
.venv/Scripts/python verify_hash.py --tamper
```

## Fund the devnet wallet (one-time)

A wallet is generated at `wallet.json` on first run and reused. The public devnet faucet is heavily rate-limited; if the automatic airdrop fails, fund the printed address once at https://faucet.solana.com and re-run. Each memo transaction costs ~0.000005 SOL, so one airdrop lasts thousands of runs.

## Files

| File | Role |
|------|------|
| `cli.py` | Interactive CLI: welcome → ask for image → search → blockchain, with full on-chain detail |
| `pipeline.py` | Orchestrates all four stages end to end |
| `face_encode.py` | YuNet detection + SFace 128-d encoding |
| `search_post.py` | Reverse image search (SerpAPI / Yandex) |
| `chain.py` | Blockchain layer: Solana devnet + local sim chain |
| `upload_hash.py` | Hash the found post and write it to chain |
| `verify_hash.py` | Re-read on-chain record and verify / detect tamper |
| `hashing_script.py` | Minimal standalone SHA-256 example |

## Known limitations

- **Search reliability** — the keyless Yandex fallback is best-effort and can return nothing (JS-rendered results). Set `SERPAPI_KEY` for dependable, social-media-rich matches.
- **Public figures search best** — reverse image search only finds people with an existing web presence; an unknown private face may return no match.
- **Devnet faucet limits** — public devnet airdrops are rate-limited per IP per day; use the web faucet or `CHAIN=local` if throttled.
- **Face match threshold** — SFace cosine ≥ 0.363 is treated as the same person (OpenCV's recommended threshold); borderline poses/lighting may fall under it.
- The query image is briefly uploaded to a public temp host to obtain a URL the search engine can fetch.
