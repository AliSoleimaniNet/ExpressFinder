<div align="center">

# 🔍 ExpressFinder

**Production-ready ExpressVPN location scanner & quality tester for Windows**

*Finds which VPN locations actually connect — fast — then benchmarks them.*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4?logo=windows)](https://www.microsoft.com/windows)
[![ExpressVPN](https://img.shields.io/badge/Requires-ExpressVPN-DA3940)](https://www.expressvpn.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 📖 Table of Contents

- [Why this tool exists](#-why-this-tool-exists)
- [Features](#-features)
- [Project structure](#-project-structure)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick start](#-quick-start)
- [Usage — all modes](#-usage--all-modes)
  - [scan — fast location scanner](#1-scan--fast-location-scanner)
  - [test — quality benchmarker](#2-test--quality-benchmarker)
  - [auto — scan then benchmark](#3-auto--scan-then-benchmark)
  - [best — show historical winners](#4-best--show-historical-winners)
- [Interactive menu (run.bat)](#-interactive-menu-runbat)
- [Command-line reference](#-command-line-reference)
- [Output files](#-output-files)
- [How history-based scoring works](#-how-history-based-scoring-works)
- [Configuration](#-configuration)
- [Legacy scripts](#-legacy-scripts)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## 💡 Why this tool exists

ExpressVPN has **220+ server locations** worldwide. In regions with heavy internet restrictions, fewer than 10 of those locations may actually be reachable at any given time.

Testing each location manually takes **hours**. ExpressFinder automates it:

1. **Scans all locations with a hard timeout** — skips dead servers in seconds instead of waiting forever.
2. **Tries historically successful locations first** — if Atlanta worked last week, it is tested in the first few minutes.
3. **Benchmarks working connections** — measures real ping, download speed, and IP info so you pick the *best* working location, not just any working one.

---

## ✨ Features

| Feature | Details |
|---|---|
| ⚡ **Fast scanning** | Hard per-location timeout (default 18 s). Previous version used `None` = infinite hang. |
| 🏆 **History-first ordering** | Parses all past `successful_connections_*.txt` files, scores each location, and tries proven winners first. |
| 📊 **Quality benchmarking** | Ping (avg + jitter), download speed (Mbps), real IP, country, ISP — all through the live tunnel. |
| 🖥️ **Interactive menu** | `run.bat` gives a numbered menu — no CLI knowledge needed. |
| 💾 **Structured output** | Timestamped scan `.txt` and quality `.json` files in `results/`, plus a dated legacy file for backwards compatibility. |
| 🔧 **Zero mandatory deps** | Works out of the box with Python stdlib; `requests` is optional (auto-installed by `run.bat`) for faster streaming speed tests. |
| 🚫 **Skip keywords** | Configurable list of locations to always skip (default: Israel). |

---

## 📁 Project structure

```
ExpressFinder/
│
├── expressfinder.py          ← Main script (v2.0) — use this
│
├── run.bat                   ← Interactive menu launcher (double-click)
│
├── requirements.txt          ← Python dependencies (requests)
│
├── results/                  ← Auto-created; all output lands here
│   ├── scan_YYYYMMDD_HHMMSS.txt
│   └── quality_YYYYMMDD_HHMMSS.json
│
├── successful_connections_YYYYMMDD.txt   ← Daily legacy output (feeds history)
├── successful_connections.txt            ← Latest scan (legacy compat)
│
├── test.py                   ← Legacy simple scanner (USA-only)
├── test.bat                  ← Launcher for test.py
├── connect.py                ← Legacy quick-connect (first working location)
└── connect.bat               ← Launcher for connect.py
```

---

## 📋 Requirements

| Requirement | Notes |
|---|---|
| **Windows 10 / 11** | ExpressVPN CLI is Windows-only |
| **ExpressVPN** (installed & activated) | CLI at `C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe` |
| **Python 3.8+** | [Download](https://python.org/downloads) — must be in PATH |
| **Administrator privileges** | Required by ExpressVPN CLI to open/close tunnels |
| `requests` *(optional)* | Streaming speed test; auto-installed by `run.bat` if missing |

---

## 🚀 Installation

```bash
# 1. Clone the repo
git clone https://github.com/AliSoleimaniNet/ExpressFinder.git
cd ExpressFinder

# 2. (Optional) Install the one dependency
pip install -r requirements.txt
```

> **No virtual environment needed.** The script falls back to `urllib` (stdlib) if `requests` is missing.

---

## ⚡ Quick start

**Option A — Double-click `run.bat`** *(recommended)*

The bat file auto-elevates to admin, installs `requests` if missing, and shows an interactive numbered menu.

**Option B — Terminal (run as Administrator)**

```powershell
# Scan all locations, history-sorted
python expressfinder.py scan

# Scan USA only
python expressfinder.py scan --filter USA

# Full pipeline: scan then quality-test working locations
python expressfinder.py auto --filter USA

# See your historically best locations
python expressfinder.py best
```

---

## 📚 Usage — all modes

### 1. `scan` — Fast location scanner

Tests every location as fast as possible. Locations with a history of success are tried **first**, so you start seeing working results within the first few minutes even when scanning all 220+ locations.

```powershell
python expressfinder.py scan
python expressfinder.py scan --filter USA
python expressfinder.py scan --filter Japan --timeout 12
```

**Live output:**
```
[  1/220]  [8× 1.5s]   ⏳ USA - Milwaukee ...         ✅ 1.31s
[  2/220]  [7× 1.4s]   ⏳ USA - Minneapolis ...        ✅ 1.28s
[  3/220]  [6× 1.6s]   ⏳ USA - Fargo ...              ❌ failed
[  4/220]  [new]        ⏳ Australia - Brisbane ...     ⏳ timeout (18s)
...

──────────────────────────────────────────────────────────
🎯  Scan done in 12m 44s — 9/220 connected

🏆  Top 10 fastest:
     1.   1.28s   USA - Minneapolis
     2.   1.31s   USA - Milwaukee
     3.   1.43s   USA - Atlanta
```

The `[8× 1.5s]` badge means this location has connected successfully 8 times historically with an average of 1.5 s connect time.

---

### 2. `test` — Quality benchmarker

Connects to one or more locations and runs a full quality suite **through the live tunnel**:

| Metric | Method |
|---|---|
| **Ping** | 4 ICMP packets to `8.8.8.8` → average ms + jitter |
| **Download speed** | Download 5 MB from Cloudflare CDN → Mbps |
| **IP / Geo** | Query `ipinfo.io` → real IP, country, ISP/org |

```powershell
# Test a single location
python expressfinder.py test "USA - New York"

# Test all locations from the most recent scan
python expressfinder.py test --from-last-scan

# Test last scan, USA only
python expressfinder.py test --from-last-scan --filter USA
```

**Live output:**
```
══════════════════════════════════════════════════════════
  [1/9]  🔷  USA - Milwaukee
──────────────────────────────────────────────────────────
   🔗 Connecting … ✅ 1.31s
   📡 Ping 8.8.8.8 × 4 … 42.3 ms  (jitter 1.2 ms)
   🌐 IP info … 198.54.x.x [US] AS20473 Vultr Holdings
   ⬇  Download speed test (5 MB) … 87.45 Mbps

══════════════════════════════════════════════════════════
  Location                            Connect    Ping   DL Mbps  IP
────────────────────────────────────────────────────────────────────
  USA - Milwaukee                      1.31s    42ms    87.45   198.54.x.x
  USA - Minneapolis                    1.28s    45ms    74.12   199.103.x.x
```

---

### 3. `auto` — Scan then benchmark

Runs `scan`, saves working locations, then immediately runs `test` on all of them. The complete pipeline in one command.

```powershell
python expressfinder.py auto
python expressfinder.py auto --filter USA
python expressfinder.py auto --no-quality    # scan only, skip quality test
```

---

### 4. `best` — Show historical winners

Reads **all** `successful_connections_*.txt` files and prints a ranked table — without connecting to anything.

```powershell
python expressfinder.py best
python expressfinder.py best --top 30
```

**Output:**
```
════════════════════════════════════════════════════════════════════════
  #    Location                                  Hits     Avg    Score  Last seen
────────────────────────────────────────────────────────────────────────
  1    USA - Milwaukee                            44×    1.3s   158.4  1d ago
  2    USA - Minneapolis                          38×    1.3s   141.2  1d ago
  3    USA - Atlanta                              35×    1.4s   131.8  3d ago
  4    Sweden - 2                                 21×    1.0s    89.6  12d ago
  5    Iceland                                    19×    1.3s    79.4  12d ago
════════════════════════════════════════════════════════════════════════
```

---

## 🖥️ Interactive menu (`run.bat`)

Double-click `run.bat`. It auto-elevates to admin and shows:

```
 ╔══════════════════════════════════════════════╗
 ║          E X P R E S S F I N D E R          ║
 ║              VPN Location Tool               ║
 ╚══════════════════════════════════════════════╝

  [1]  Fast Scan  — ALL locations  (history-sorted)
  [2]  Fast Scan  — USA only
  [3]  Fast Scan  — custom filter
  [4]  Fast Scan  — faster timeout (12s, more misses)
  ─────────────────────────────────────────────
  [5]  Quality Test — from last scan results
  [6]  Quality Test — single location
  ─────────────────────────────────────────────
  [7]  Auto mode  — Scan ALL then quality test
  [8]  Auto mode  — USA scan then quality test
  ─────────────────────────────────────────────
  [9]  Show best locations  (from history)
  [0]  Exit
```

After each operation you are returned to the menu automatically.

---

## 🔧 Command-line reference

```
python expressfinder.py <mode> [options]

Modes:
  scan                  Fast-scan all (or filtered) locations
  test  [location]      Quality-test one or more locations
  auto                  Scan then quality-test working locations
  best                  Print ranked history table

Options:
  --filter  / -f  KW    Only include locations containing KW (case-insensitive)
  --timeout / -t  N     Connect timeout in seconds (default: 18)
  --top           N     Rows to show in 'best' mode (default: 20)
  --from-last-scan      Load locations from most recent scan file
  --no-quality          Skip quality tests in 'auto' mode
  --protocol    / -p P  Protocol label to record in output (default: Auto)
```

**More examples:**

```powershell
python expressfinder.py scan --filter "United Kingdom"
python expressfinder.py scan --filter Canada --timeout 15
python expressfinder.py test "USA - Atlanta"
python expressfinder.py test --from-last-scan --filter USA
python expressfinder.py auto --no-quality
python expressfinder.py best --top 50
```

---

## 💾 Output files

### `results/scan_YYYYMMDD_HHMMSS.txt`

Created after every `scan` or `auto` run.

```
Location, Protocol, TimeToConnectSeconds, Timestamp
USA - Milwaukee, Auto, 1.31, 2026-05-27T14:31:02
USA - Minneapolis, Auto, 1.28, 2026-05-27T14:32:15
```

### `results/quality_YYYYMMDD_HHMMSS.json`

Created after every `test` or `auto` run.

```json
[
  {
    "location": "USA - Milwaukee",
    "protocol": "Auto",
    "connect_time": 1.31,
    "ping_ms": 42.3,
    "ping_jitter_ms": 1.2,
    "download_mbps": 87.45,
    "ip_address": "198.54.x.x",
    "country": "US",
    "org": "AS20473 Vultr Holdings",
    "timestamp": "2026-05-27T14:33:10"
  }
]
```

### `successful_connections_YYYYMMDD.txt`

One file per day, created after each scan. Matches the legacy CSV format. **This is what feeds the history scoring engine on future runs** — the more scans you accumulate, the smarter the ordering becomes.

```
Location, Protocol, TimeToConnectSeconds
USA - Milwaukee, Auto, 1.31
USA - Minneapolis, Auto, 1.28
```

---

## 🧮 How history-based scoring works

On startup, `expressfinder.py` reads every `successful_connections_*.txt` file in the project folder and builds a score for each location:

```
score = (success_count  ×  3.00)
      + (max(0, 365 − age_days)  ×  0.20)
      + (max(0, 20 − avg_connect_time)  ×  0.40)
```

| Component | Meaning |
|---|---|
| **Success count** | More past successes = higher priority |
| **Recency** | Location that worked yesterday scores higher than one from 3 months ago |
| **Speed bonus** | Locations averaging under 20 s to connect get an extra boost |

Locations with **no history** are appended at the end of the scan queue. Over time, as you accumulate scan files, the ordering becomes increasingly accurate for your specific network environment.

---

## ⚙️ Configuration

All tunable constants are at the top of `expressfinder.py`:

```python
CLI_PATH          = r"C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe"
CONNECT_TIMEOUT   = 18     # seconds — main scan speed lever
DISCONNECT_TO     = 8
PING_HOST         = "8.8.8.8"
PING_COUNT        = 4
DOWNLOAD_URL      = "https://speed.cloudflare.com/__down?bytes=5000000"  # 5 MB
DOWNLOAD_TIMEOUT  = 30
SKIP_KEYWORDS     = ["israel"]   # locations containing these are always skipped
```

**Tuning guide:**

| Goal | Change |
|---|---|
| Scan faster, accept more misses | Lower `CONNECT_TIMEOUT` to 10–12 |
| Catch slow-but-working servers | Raise `CONNECT_TIMEOUT` to 25–30 |
| More accurate speed test | Change URL bytes to `25000000` (25 MB) |
| Different ping target | Change `PING_HOST` to e.g. `1.1.1.1` |
| Skip additional regions | Add entries to `SKIP_KEYWORDS` |

---

## 🗂️ Legacy scripts

Kept for simple use cases:

| File | What it does |
|---|---|
| `test.py` + `test.bat` | Scans USA locations only; no history ordering, no quality test. |
| `connect.py` + `connect.bat` | Tries every location with `LightwayUdp` and stops at the first successful connection. Useful for a quick "just get me online" scenario. |

> All active development is in `expressfinder.py`.

---

## ❓ FAQ

**Q: Can I test multiple locations at the same time?**

No — this is a hard limitation of ExpressVPN itself. The daemon supports exactly **one active tunnel**. Calling `connect` while already connected simply switches servers. The only true parallelism would require separate VMs or machines each running their own ExpressVPN instance.

ExpressFinder compensates by making every individual test as fast as possible and by front-loading historically proven locations.

---

**Q: Why does `scan` show `⏳ timeout` for most locations?**

In heavily restricted networks, most of the 220+ endpoints are blocked at the network level. A timeout simply means the server did not respond within the timeout window. This is expected. The goal of `scan` is to quickly surface the handful that *do* work.

---

**Q: How do I make scanning faster?**

```powershell
python expressfinder.py scan --timeout 12
```

Dropping from 18 s to 12 s cuts worst-case time per failed location by 33 %. The trade-off: servers that take 13–17 s to connect will be incorrectly skipped. Use `best` mode to review which locations consistently connect in under 5 s and lower the timeout accordingly.

---

**Q: The CLI path is wrong on my machine.**

Edit the `CLI_PATH` constant at the top of `expressfinder.py`:

```python
CLI_PATH = r"C:\Your\Custom\Path\To\ExpressVPN.CLI.exe"
```

---

**Q: `requests` is not installed — will the script still work?**

Yes. All HTTP calls fall back to Python's built-in `urllib`. The only visible difference is the speed test reads the full download into memory before timing it, which is slightly less accurate for very fast connections. `run.bat` installs `requests` automatically on first launch.

---

**Q: Is this an official ExpressVPN product?**

No. This is an independent open-source project that uses the official `ExpressVPN.CLI.exe` binary installed by the ExpressVPN Windows client. It does not modify, patch, or reverse-engineer ExpressVPN in any way.

---

## 🤝 Contributing

Pull requests are welcome.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add your feature"`
4. Push and open a PR

Please maintain the zero-mandatory-dependencies policy — any new optional dependency must degrade gracefully when absent.

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<div align="center">

Made with ☕ to survive restricted networks.

</div>
