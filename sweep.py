#!/usr/bin/env python3
import json, re, sys, os, time, signal, random, subprocess, argparse
from pathlib import Path
from datetime import datetime, timezone

RATE_S       = float(os.getenv("RATE_S", "0.15"))
MAX_RETRIES  = 3
OUTPUT       = Path(os.getenv("OUTPUT", "results.jsonl"))
STATE_FILE   = Path(".sweep_state.json")
LOG_FILE     = Path("sweep.log")
CHECKPOINT_N = 200

UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

state     = {"completed": [], "failed": [], "last_id": None, "started": None}
completed = set()
running   = True

def load_state():
    global state, completed
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            completed = set(state.get("completed", []))
        except Exception:
            pass

def save_state():
    state["completed"] = list(completed)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, STATE_FILE)

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    with LOG_FILE.open("a") as f:
        f.write(f"[{ts}] {msg}\n")

def handle_signal(sig, _):
    global running
    sys.stderr.write("\n")
    save_state()
    running = False

signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGHUP,  handle_signal)

def extract_json_obj(text, pattern):
    m = re.search(pattern + r'\s*', text)
    if not m:
        return None
    start = m.end()
    if start >= len(text) or text[start] != '{':
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == '{':   depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                try:    return json.loads(text[start:i+1])
                except: return None
    return None

def fetch(result_id):
    ua  = random.choice(UA_POOL)
    url = f"https://www.speedtest.net/result/{result_id}"
    for attempt in range(MAX_RETRIES):
        try:
            r = subprocess.run(
                ["/usr/bin/curl", "-s", "-L", "-A", ua,
                 "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                 "-H", "Accept-Language: en-US,en;q=0.9",
                 "-H", "Accept-Encoding: gzip, deflate, br",
                 "-H", "Connection: keep-alive",
                 "-H", "Upgrade-Insecure-Requests: 1",
                 "--compressed",
                 "--max-time", "20",
                 "-w", "\n__S__%{http_code}", url],
                capture_output=True, text=True, timeout=25
            )
            parts = r.stdout.rsplit("\n__S__", 1)
            html  = parts[0] if len(parts) == 2 else ""
            code  = int(parts[1].strip()) if len(parts) == 2 else 0
            if code == 200 and html: return html, 200
            if code == 404:          return None, 404
            if code == 403:
                time.sleep(5.0 + random.random() * 3)
                continue
            time.sleep(min(60.0, (2 ** attempt) + random.random() * 2))
        except subprocess.TimeoutExpired:
            time.sleep(5.0)
        except Exception as e:
            log(f"err {result_id} attempt {attempt}: {e}")
            time.sleep(2.0)
    return None, 0

def parse(result_id, html):
    init = extract_json_obj(html, r'window\.OOKLA\.INIT_DATA\s*=')
    if not init:
        return None
    res  = init.get("result", {})
    dl_k = res.get("download") or 0
    ul_k = res.get("upload")   or 0
    ts   = res.get("date")
    dt   = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
    return {
        "id":           str(result_id),
        "ts":           ts,
        "datetime":     dt,
        "dl_mbps":      round(dl_k / 1000, 2),
        "ul_mbps":      round(ul_k / 1000, 2),
        "ping_ms":      res.get("latency"),
        "idle_lat_ms":  res.get("idle_latency"),
        "dl_lat_ms":    res.get("download_latency"),
        "ul_lat_ms":    res.get("upload_latency"),
        "server":       res.get("server_name"),
        "sponsor":      res.get("sponsor_name"),
        "isp":          res.get("isp_name"),
        "connection":   res.get("connection_mode"),
        "conn_type":    res.get("connection_icon"),
        "url":          f"https://www.speedtest.net/result/{result_id}",
    }

def main():
    global running
    p = argparse.ArgumentParser()
    p.add_argument("--start",  type=int, required=True)
    p.add_argument("--count",  type=int, default=50000)
    p.add_argument("--rate",   type=float, default=RATE_S)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    if args.resume:
        load_state()
    if not state.get("started"):
        state["started"] = datetime.now(timezone.utc).isoformat()

    ids     = list(range(args.start, args.start - args.count, -1))
    pending = [i for i in ids if i not in completed]

    print(f"🟢 {len(pending)} pending | output={OUTPUT}")

    n_ok = n_miss = n_err = 0
    t0 = time.time()

    with OUTPUT.open("a") as fout:
        for i, result_id in enumerate(pending):
            if not running:
                break
            state["last_id"] = result_id
            elapsed = time.time() - t0
            rps = (n_ok + n_miss + n_err) / max(elapsed, 1)
            sys.stderr.write(
                f"\r  {result_id}  ok={n_ok} miss={n_miss} err={n_err}  {rps:.1f}req/s  {i}/{len(pending)}"
            )
            sys.stderr.flush()

            # jitter - looks more organic
            jitter = random.uniform(0.8, 1.4)
            html, code = fetch(result_id)
            time.sleep(args.rate * jitter)

            if code == 404 or html is None:
                n_miss += 1
                completed.add(result_id)
                continue

            record = parse(result_id, html)
            if record:
                fout.write(json.dumps(record) + "\n")
                fout.flush()
                n_ok += 1
                completed.add(result_id)
            else:
                n_err += 1
                state.setdefault("failed", []).append(result_id)

            if (n_ok + n_miss) % CHECKPOINT_N == 0:
                save_state()

    save_state()
    sys.stderr.write("\n")
    elapsed = time.time() - t0
    print(f"\n🟢 done | ok={n_ok} miss={n_miss} err={n_err} | {elapsed:.0f}s | {OUTPUT}")

if __name__ == "__main__":
    main()
