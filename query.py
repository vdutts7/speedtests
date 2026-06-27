#!/usr/bin/env python3
import json, sys, argparse, statistics
from pathlib import Path

def load(path, filters):
    records = []
    p = Path(path)
    if not p.exists():
        print(f"not found: {path}"); sys.exit(1)
    with p.open() as f:
        for line in f:
            try:
                r = json.loads(line)
                isp = (r.get("isp") or r.get("isp_display") or "")
                srv = (r.get("server") or "")
                if filters.get("isp") and filters["isp"].lower() not in isp.lower(): continue
                if filters.get("server") and filters["server"].lower() not in srv.lower(): continue
                records.append(r)
            except Exception:
                pass
    return records

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals: return {}
    s = sorted(vals)
    return {
        "n": len(vals),
        "min": round(min(vals), 1),
        "mean": round(statistics.mean(vals), 1),
        "median": round(statistics.median(vals), 1),
        "p95": round(s[int(len(vals)*0.95)], 1),
        "max": round(max(vals), 1),
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input",  default="results.jsonl")
    p.add_argument("--isp",    help="filter by ISP (partial)")
    p.add_argument("--server", help="filter by server (partial)")
    p.add_argument("--top",    type=int, help="top N by download")
    p.add_argument("--csv",    action="store_true")
    args = p.parse_args()

    filters = {k: v for k, v in {"isp": args.isp, "server": args.server}.items() if v}
    records = load(args.input, filters)
    if not records:
        print("no records match"); return

    if args.csv:
        fields = ["id","datetime","dl_mbps","ul_mbps","ping_ms",
                  "idle_lat_ms","dl_lat_ms","ul_lat_ms","server","sponsor","isp","connection","conn_type","url"]
        print(",".join(fields))
        for r in records:
            print(",".join(str(r.get(f,"")) for f in fields))
        return

    if args.top:
        for r in sorted(records, key=lambda x: x.get("dl_mbps") or 0, reverse=True)[:args.top]:
            isp = r.get("isp") or r.get("isp_display") or "?"
            print(f"{r['id']:>14}  {r.get('dl_mbps',0):7.1f}↓  {r.get('ul_mbps',0):7.1f}↑"
                  f"  {r.get('ping_ms','?'):>4}ms  {isp:<24}  {r.get('server','?')}")
        return

    isp_key = lambda r: r.get("isp") or r.get("isp_display") or "?"
    isp_counts, srv_counts = {}, {}
    for r in records:
        isp_counts[isp_key(r)] = isp_counts.get(isp_key(r), 0) + 1
        srv = r.get("server") or "?"
        srv_counts[srv] = srv_counts.get(srv, 0) + 1

    print(f"\n  records: {len(records)}")
    for label, vals in [
        ("DOWNLOAD Mbps", [r["dl_mbps"] for r in records]),
        ("UPLOAD Mbps",   [r["ul_mbps"] for r in records]),
        ("PING ms",       [float(r["ping_ms"]) for r in records if r.get("ping_ms") is not None]),
    ]:
        s = stats(vals)
        if s:
            print(f"\n  {label}")
            print(f"    min={s['min']}  mean={s['mean']}  median={s['median']}  p95={s['p95']}  max={s['max']}")

    print(f"\n  TOP ISPs")
    for isp, n in sorted(isp_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {n/len(records)*100:5.1f}%  ({n:4})  {isp}")

    print(f"\n  TOP servers")
    for srv, n in sorted(srv_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {n/len(records)*100:5.1f}%  ({n:4})  {srv}")
    print()

if __name__ == "__main__":
    main()
