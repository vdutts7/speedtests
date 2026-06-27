<p align="center">
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/ookla-speedtest.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/xfinity.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/airtel.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/verizon.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/orange.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/vodafone.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/movistar.webp" alt="logo" width="80" height="80" />
  <img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/telmex.webp" alt="logo" width="80" height="80" />
</p>
<h1 align="center">speedtests</h1>
<p align="center"><em>crawl public speedtest result pages → ISP intelligence map</em></p>

---

![preview](https://res.cloudinary.com/ddyc1es5v/image/upload/v1782552753/gh-repos/speedtests/speedtests-preview.webp)

## Issue

public [speedtest.net](https://www.speedtest.net) result pages embed `window.OOKLA.INIT_DATA` JSON with no auth

result IDs opaque; no bulk export API

❌ one-off lookups: can't build ISP/regional aggregates from manual page visits

❌ third-party datasets: stale, licensed, or missing server/latency fields you need

❌ naive crawl: 403/rate limits on sequential IDs; gaps without checkpoint/resume

## How it works

anchor from your own run:

1. open [speedtest.net](https://www.speedtest.net), run a test
2. result URL in the bar- trailing digits are the ID (`/result/19360616699`)
3. pass that ID to `sweep.py --start`
4. sweep decrements by 1 each fetch (`19360616699`, `19360616698`, …)
5. each `/result/{id}` hit parses into `data/*.jsonl`

```text
+-------------+     +----------+     +--------+     +----------+
| your result | --> | sweep.py | --> |  data/ | --> | query.py |
|     ID      |     | decrement|     | jsonl  |     |          |
+-------------+     +----------+     +--------+     +----------+
```

## Setup

```bash
python3 --version   # stdlib only; sweep shells out to /usr/bin/curl
```

## Run

```bash
# --start = ID from your own speedtest.net result URL
OUTPUT=data/ookla_results.jsonl python3 sweep.py --start 19360616699 --count 50000
```

```bash
OUTPUT=data/ookla_results.jsonl python3 sweep.py --start 19360616699 --count 50000 --resume
```

```bash
python3 query.py --input data/ookla_results.jsonl --isp Airtel
python3 query.py --input data/ookla_results.jsonl --top 20
python3 query.py --input data/ookla_results.jsonl --csv > airtel_export.csv
```

## Gotchas

| symptom | fix | stability | why |
|---|---|---|---|
| 403 bursts | lower `RATE_S` or `--rate` | intermittent | speedtest.net edge throttle |
| sparse hit rate | re-run your own test; use fresher `--start` ID | stable | not every decremented ID exists |

## Tools Used

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>

## Contact

<a href="https://vd7.io"><img src="https://res.cloudinary.com/ddyc1es5v/image/upload/v1773910810/readme-badges/readme-badge-vd7.png" alt="vd7.io" height="40" /></a> &nbsp;
<a href="https://x.com/vdutts7"><img src="https://res.cloudinary.com/ddyc1es5v/image/upload/v1773910817/readme-badges/readme-badge-x.png" alt="/vdutts7" height="40" /></a>
