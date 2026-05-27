#!/usr/bin/env python3
"""
ExpressFinder v2.0
==================
Production-ready ExpressVPN location scanner & quality tester.

Modes
-----
  scan   Fast-scan all (or filtered) locations, sorted by history.
  test   Deep quality test: ping, download speed, IP info.
  auto   scan → then quality-test every working location.
  best   Print best locations ranked from all historical data.

Examples
--------
  python expressfinder.py scan
  python expressfinder.py scan --filter USA --timeout 12
  python expressfinder.py test "USA - New York"
  python expressfinder.py test --from-last-scan
  python expressfinder.py auto --filter USA
  python expressfinder.py best --top 20
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── optional: requests (nicer streaming download) ────────────────────────────
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ═════════════════════════════════════════════════════════════════════════════
#  CONFIG  (edit these to customise)
# ═════════════════════════════════════════════════════════════════════════════

CLI_PATH          = r"C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe"
RESULTS_DIR       = Path("results")
HISTORY_GLOB      = "successful_connections*.txt"

CONNECT_TIMEOUT   = 18    # seconds — main lever for scan speed
DISCONNECT_TO     = 8
LIST_TIMEOUT      = 20

PING_HOST         = "8.8.8.8"
PING_COUNT        = 4
DOWNLOAD_URL      = "https://speed.cloudflare.com/__down?bytes=5000000"   # 5 MB
DOWNLOAD_TIMEOUT  = 30

IP_INFO_URL       = "https://ipinfo.io/json"
IP_TIMEOUT        = 8

SKIP_KEYWORDS     = ["israel"]   # case-insensitive; locations that contain
                                  # any of these are always skipped

# Scoring weights for history-based ordering
SCORE_W_RECENT    =  0.20    # bonus per day closer to today (capped at 365)
SCORE_W_COUNT     =  3.00    # per historical success
SCORE_W_SPEED     =  0.40    # per second faster than 20 s baseline

# ═════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class ScanResult:
    location : str
    protocol : str
    elapsed  : float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class QualityResult:
    location        : str
    protocol        : str
    connect_time    : float
    ping_ms         : Optional[float]
    ping_jitter_ms  : Optional[float]
    download_mbps   : Optional[float]
    ip_address      : Optional[str]
    country         : Optional[str]
    org             : Optional[str]
    timestamp       : str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class LocationScore:
    name         : str
    success_count: int            = 0
    avg_time     : float          = 99.0
    last_seen    : Optional[datetime] = None
    score        : float          = 0.0

# ═════════════════════════════════════════════════════════════════════════════
#  VPN MANAGER
# ═════════════════════════════════════════════════════════════════════════════

class VPNManager:
    """Thin wrapper around the ExpressVPN CLI."""

    def __init__(self, cli: str = CLI_PATH) -> None:
        self.cli = cli
        if not Path(cli).exists():
            print(f"⚠  CLI not found: {cli}")

    # ── internal ──────────────────────────────────────────────────────────────

    def _run(self, args: List[str], timeout: Optional[int] = 10) -> str:
        """
        Run CLI command.
        timeout=None  → wait forever (no limit).
        timeout=N     → raise after N seconds.
        """
        cmd = [self.cli] + args
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,          # None = no timeout
                encoding="utf-8",
                errors="replace",
            )
            return (r.stdout + r.stderr).strip()
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except FileNotFoundError:
            return "ERROR: CLI not found"
        except Exception as exc:
            return f"ERROR: {exc}"

    # ── public ────────────────────────────────────────────────────────────────

    def list_locations(self) -> List[str]:
        """Return all location names from `expressvpn list`."""
        out = self._run(["list"], timeout=LIST_TIMEOUT)
        locations: List[str] = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.endswith(":"):
                continue
            m = re.match(r"^(.+?)\s+\d+$", line)
            if m:
                name = m.group(1).strip()
                if any(kw in name.lower() for kw in SKIP_KEYWORDS):
                    continue
                locations.append(name)
        return locations

    def connect(
        self,
        location: str,
        protocol: Optional[str] = None,
        timeout : Optional[int] = CONNECT_TIMEOUT,
    ) -> Tuple[bool, float, str]:
        """
        Connect to *location*.
        timeout=None → no timeout (wait forever).
        Returns (success, elapsed_seconds, raw_output).
        """
        args = ["connect", location]
        t0   = time.time()
        out  = self._run(args, timeout=timeout)
        elapsed = round(time.time() - t0, 2)
        success = "Connected" in out or "متصل" in out
        return success, elapsed, out

    def disconnect(self) -> str:
        return self._run(["disconnect"], timeout=DISCONNECT_TO)

    def status(self) -> bool:
        out = self._run(["status"], timeout=5)
        return "Connected" in out or "متصل" in out

# ═════════════════════════════════════════════════════════════════════════════
#  HISTORY MANAGER
# ═════════════════════════════════════════════════════════════════════════════

class HistoryManager:
    """
    Reads all successful_connections*.txt files, builds a score per location,
    and provides sorted location lists.
    """

    def __init__(self, base_dir: Path = Path(".")) -> None:
        self.base_dir = base_dir
        self._scores: Dict[str, LocationScore] = {}
        self._load_all()

    # ── loading ───────────────────────────────────────────────────────────────

    @staticmethod
    def _date_from_filename(name: str) -> Optional[datetime]:
        m = re.search(r"(\d{8})", name)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y%m%d")
            except ValueError:
                pass
        return None

    def _load_all(self) -> None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        files = sorted(self.base_dir.glob(HISTORY_GLOB))

        for fpath in files:
            file_date = self._date_from_filename(fpath.name) or today
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("Location"):
                            continue
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) < 2:
                            continue
                        loc = parts[0]
                        try:
                            connect_time = float(parts[2]) if len(parts) > 2 else 15.0
                        except (ValueError, IndexError):
                            connect_time = 15.0

                        if loc not in self._scores:
                            self._scores[loc] = LocationScore(name=loc)
                        s = self._scores[loc]
                        # Running average of connect time
                        s.avg_time = (s.avg_time * s.success_count + connect_time) / (s.success_count + 1)
                        s.success_count += 1
                        if s.last_seen is None or file_date > s.last_seen:
                            s.last_seen = file_date
            except Exception:
                continue

        # Compute composite score
        for s in self._scores.values():
            age_days = (today - s.last_seen).days if s.last_seen else 365
            recency  = max(0.0, 365 - age_days) * SCORE_W_RECENT
            count    = s.success_count * SCORE_W_COUNT
            speed    = max(0.0, 20.0 - s.avg_time) * SCORE_W_SPEED
            s.score  = recency + count + speed

    # ── public ────────────────────────────────────────────────────────────────

    def sort_locations(self, locations: List[str]) -> List[str]:
        """
        Return *locations* with known-good ones first (desc score),
        then unknowns appended at the end.
        """
        known   = sorted(
            [(loc, self._scores[loc].score) for loc in locations if loc in self._scores],
            key=lambda x: x[1],
            reverse=True,
        )
        unknown = [loc for loc in locations if loc not in self._scores]
        return [loc for loc, _ in known] + unknown

    def top(self, n: int = 20) -> List[LocationScore]:
        return sorted(self._scores.values(), key=lambda s: s.score, reverse=True)[:n]

    def get(self, loc: str) -> Optional[LocationScore]:
        return self._scores.get(loc)

# ═════════════════════════════════════════════════════════════════════════════
#  QUALITY TESTER
# ═════════════════════════════════════════════════════════════════════════════

class QualityTester:
    """Measures ping, download speed and IP geo-info through the active tunnel."""

    # ── ping ──────────────────────────────────────────────────────────────────

    def ping(
        self,
        host : str = PING_HOST,
        count: int = PING_COUNT,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Return (avg_ms, jitter_ms) or (None, None)."""
        is_win = platform.system() == "Windows"
        cmd    = ["ping", "-n" if is_win else "-c", str(count), host]
        try:
            r   = subprocess.run(cmd, capture_output=True, text=True, timeout=count * 4 + 5)
            out = r.stdout

            if is_win:
                rtts      = re.findall(r"time[=<](\d+)ms", out, re.I)
                avg_match = re.search(r"Average\s*=\s*(\d+)\s*ms", out, re.I)
            else:
                rtts      = re.findall(r"time=([\d.]+)\s*ms", out)
                avg_match = re.search(r"min/avg/max[^/]*/([^/]+)/", out)

            if rtts:
                vals   = [float(x) for x in rtts]
                avg    = float(avg_match.group(1)) if avg_match else statistics.mean(vals)
                jitter = round(statistics.stdev(vals), 1) if len(vals) > 1 else 0.0
                return round(avg, 1), jitter
        except Exception:
            pass
        return None, None

    # ── download speed ────────────────────────────────────────────────────────

    def download_speed(
        self,
        url    : str = DOWNLOAD_URL,
        timeout: int = DOWNLOAD_TIMEOUT,
    ) -> Optional[float]:
        """Download a test file; return speed in Mbps or None."""
        try:
            if HAS_REQUESTS:
                t0    = time.time()
                resp  = _requests.get(url, stream=True, timeout=timeout)
                resp.raise_for_status()
                total = sum(len(chunk) for chunk in resp.iter_content(65536))
            else:
                t0   = time.time()
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    total = len(resp.read())

            elapsed = time.time() - t0
            if elapsed > 0 and total > 0:
                return round((total * 8) / (elapsed * 1_000_000), 2)
        except Exception:
            pass
        return None

    # ── IP / geo ──────────────────────────────────────────────────────────────

    def ip_info(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (ip, country, org) or (None, None, None)."""
        try:
            if HAS_REQUESTS:
                data = _requests.get(IP_INFO_URL, timeout=IP_TIMEOUT).json()
            else:
                with urllib.request.urlopen(IP_INFO_URL, timeout=IP_TIMEOUT) as r:
                    data = json.loads(r.read().decode())
            return data.get("ip"), data.get("country"), data.get("org")
        except Exception:
            pass
        return None, None, None

    # ── combined ──────────────────────────────────────────────────────────────

    def run_all(
        self,
        location    : str,
        protocol    : str,
        connect_time: float,
    ) -> QualityResult:
        print(f"   📡 Ping {PING_HOST} × {PING_COUNT} ...", end=" ", flush=True)
        ping_ms, jitter = self.ping()
        if ping_ms:
            print(f"{ping_ms} ms  (jitter {jitter} ms)")
        else:
            print("failed")

        print(f"   🌐 IP info ...", end=" ", flush=True)
        ip, country, org = self.ip_info()
        print(f"{ip} [{country}] {org}" if ip else "failed")

        print(f"   ⬇  Download speed test (5 MB) ...", end=" ", flush=True)
        dl = self.download_speed()
        print(f"{dl} Mbps" if dl else "failed")

        return QualityResult(
            location       = location,
            protocol       = protocol,
            connect_time   = connect_time,
            ping_ms        = ping_ms,
            ping_jitter_ms = jitter,
            download_mbps  = dl,
            ip_address     = ip,
            country        = country,
            org            = org,
        )

# ═════════════════════════════════════════════════════════════════════════════
#  PERSISTENCE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)


def save_scan(results: List[ScanResult]) -> Path:
    _ensure_results_dir()
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    path  = RESULTS_DIR / f"scan_{ts}.txt"

    with open(path, "w", encoding="utf-8") as f:
        f.write("Location, Protocol, TimeToConnectSeconds, Timestamp\n")
        for r in results:
            f.write(f"{r.location}, {r.protocol}, {r.elapsed}, {r.timestamp}\n")

    # Keep legacy file up-to-date for backwards compatibility
    today_file = Path(f"successful_connections_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(today_file, "w", encoding="utf-8") as f:
        f.write("Location, Protocol, TimeToConnectSeconds\n")
        for r in results:
            f.write(f"{r.location}, {r.protocol}, {r.elapsed}\n")

    print(f"\n💾  Scan   → {path}")
    print(f"💾  Legacy → {today_file}")
    return path


def save_quality(results: List[QualityResult]) -> Path:
    _ensure_results_dir()
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"quality_{ts}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)

    print(f"💾  Quality → {path}")
    return path


def load_last_scan() -> List[str]:
    """Return location names from the most recent results/scan_*.txt file."""
    _ensure_results_dir()
    files = sorted(RESULTS_DIR.glob("scan_*.txt"))
    if not files:
        # fallback: today's legacy file
        today = Path(f"successful_connections_{datetime.now().strftime('%Y%m%d')}.txt")
        files = [today] if today.exists() else sorted(Path(".").glob("successful_connections_*.txt"))
    if not files:
        return []
    latest = files[-1]
    print(f"📂  Loading last scan: {latest}")
    locs: List[str] = []
    with open(latest, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Location"):
                continue
            locs.append(line.split(",")[0].strip())
    return locs

# ═════════════════════════════════════════════════════════════════════════════
#  MODES
# ═════════════════════════════════════════════════════════════════════════════

def _resolve_timeout(timeout: int) -> Optional[int]:
    """Convert timeout value: -1 means no limit (None), otherwise use as-is."""
    return None if timeout == -1 else timeout


def mode_scan(
    vpn       : VPNManager,
    history   : HistoryManager,
    filter_kw : Optional[str] = None,
    timeout   : int           = CONNECT_TIMEOUT,
    protocol  : str           = "Auto",
    retry     : int           = 0,
) -> List[ScanResult]:
    """Fast-scan every location (optionally filtered), history-first."""

    actual_timeout = _resolve_timeout(timeout)
    timeout_label  = "no limit" if actual_timeout is None else f"{actual_timeout}s"

    print("📋  Fetching VPN location list ...")
    all_locs = vpn.list_locations()

    if filter_kw:
        all_locs = [l for l in all_locs if filter_kw.lower() in l.lower()]

    if not all_locs:
        print("❌  No locations found after filtering.")
        return []

    # Sort: historical winners first
    ordered = history.sort_locations(all_locs)
    total   = len(ordered)
    known   = sum(1 for l in ordered if history.get(l))

    print(f"✅  {total} locations to scan  |  {known} have history (tried first)")
    print(f"⏱   Connect timeout: {timeout_label} per location"
          + (f"  |  retry: {retry}x" if retry > 0 else "") + "\n")

    results: List[ScanResult] = []
    t_start = time.time()

    for i, loc in enumerate(ordered, 1):
        s     = history.get(loc)
        badge = f"[{s.success_count}x {s.avg_time:.0f}s]" if s else "[new]"
        print(f"[{i:>3}/{total}]  {badge:<12}  [{loc}] ...", end=" ", flush=True)

        ok      = False
        elapsed = 0.0
        out     = ""

        for attempt in range(retry + 1):
            if attempt > 0:
                vpn.disconnect()
                print(f"  retry {attempt}/{retry} ...", end=" ", flush=True)

            ok, elapsed, out = vpn.connect(loc, timeout=actual_timeout)
            if ok:
                break

        if "TIMEOUT" in out and not ok:
            print(f"⏳ timeout ({timeout_label})")
        elif ok:
            print(f"✅ {elapsed}s")
            results.append(ScanResult(location=loc, protocol=protocol, elapsed=elapsed))
        else:
            print(f"❌ failed")

        vpn.disconnect()

    total_time = round(time.time() - t_start)
    mins, secs = divmod(total_time, 60)

    print(f"\n{'-'*58}")
    print(f"🎯  Scan done in {mins}m {secs}s  --  {len(results)}/{total} connected")

    if results:
        results.sort(key=lambda r: r.elapsed)
        print(f"\n🏆  Top 10 fastest:")
        for rank, r in enumerate(results[:10], 1):
            print(f"    {rank:>2}. {r.elapsed:>6.2f}s   {r.location}")

    return results


def mode_test(
    vpn      : VPNManager,
    tester   : QualityTester,
    history  : HistoryManager,
    locations: List[str],
    protocol : str           = "Auto",
    timeout  : int           = CONNECT_TIMEOUT,
    retry    : int           = 0,
) -> List[QualityResult]:
    """Deep quality test for a list of locations."""
    actual_timeout = _resolve_timeout(timeout)
    timeout_label  = "no limit" if actual_timeout is None else f"{actual_timeout}s"

    # Sort by history so best candidates are tested first
    locations = history.sort_locations(locations)
    results: List[QualityResult] = []
    total = len(locations)

    for i, loc in enumerate(locations, 1):
        print(f"\n{'='*58}")
        print(f"  [{i}/{total}]  {loc}")
        print(f"{'-'*58}")

        ok      = False
        elapsed = 0.0
        out     = ""

        for attempt in range(retry + 1):
            if attempt > 0:
                vpn.disconnect()
                print(f"   🔗 Retry {attempt}/{retry} ...", end=" ", flush=True)
            else:
                print(f"   🔗 Connecting (timeout: {timeout_label}) ...", end=" ", flush=True)

            ok, elapsed, out = vpn.connect(loc, timeout=actual_timeout)
            if ok:
                break

        if not ok:
            print(f"⏳ timeout" if "TIMEOUT" in out else "❌ failed")
            vpn.disconnect()
            continue

        print(f"✅ {elapsed}s")

        qr = tester.run_all(loc, protocol, elapsed)
        results.append(qr)

        vpn.disconnect()

    return results


def mode_best(history: HistoryManager, top: int = 20) -> None:
    """Print top locations by historical score."""
    best = history.top(top)
    if not best:
        print("❌  No historical data found.")
        return

    W = 40
    print(f"\n{'═'*72}")
    print(f"  {'#':<4} {'Location':<{W}} {'Hits':>5}  {'Avg':>7}  {'Score':>7}  Last seen")
    print(f"{'─'*72}")
    for i, s in enumerate(best, 1):
        age = f"{(datetime.now() - s.last_seen).days}d ago" if s.last_seen else "unknown"
        print(f"  {i:<4} {s.name:<{W}} {s.success_count:>5}×  {s.avg_time:>6.1f}s  {s.score:>7.1f}  {age}")
    print(f"{'═'*72}\n")

# ═════════════════════════════════════════════════════════════════════════════
#  QUALITY SUMMARY TABLE
# ═════════════════════════════════════════════════════════════════════════════

def print_quality_table(results: List[QualityResult]) -> None:
    if not results:
        return
    # Sort by download speed desc, then ping asc
    ranked = sorted(
        results,
        key=lambda r: (-(r.download_mbps or 0), r.ping_ms or 9999),
    )
    print(f"\n{'═'*80}")
    print(f"  {'Location':<35} {'Connect':>8} {'Ping':>7} {'DL Mbps':>9} {'IP'}")
    print(f"{'─'*80}")
    for r in ranked:
        ping_s  = f"{r.ping_ms:.0f}ms"  if r.ping_ms        else "N/A"
        dl_s    = f"{r.download_mbps}"  if r.download_mbps   else "N/A"
        ip_s    = r.ip_address          if r.ip_address      else "N/A"
        print(f"  {r.location:<35} {r.connect_time:>7.2f}s {ping_s:>7} {dl_s:>9}  {ip_s}")
    print(f"{'═'*80}\n")

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

BANNER = """
  +--------------------------------------------------+
  |                                                  |
  |   ExpressFinder  v2.0                            |
  |   VPN Location Scanner & Quality Tester          |
  |                                                  |
  +--------------------------------------------------+
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="expressfinder",
        description="ExpressFinder — VPN location scanner & quality tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mode", choices=["scan", "test", "auto", "best"])
    parser.add_argument("location", nargs="?",
                        help="Location name for 'test' mode (quote if it has spaces)")
    parser.add_argument("--filter",  "-f", metavar="KW",
                        help="Filter locations by keyword, e.g. USA, UK, Japan")
    parser.add_argument("--timeout", "-t", type=int, default=CONNECT_TIMEOUT,
                        help=f"Connect timeout per location in seconds. "
                             f"Use -1 for no timeout (wait forever). Default: {CONNECT_TIMEOUT}")
    parser.add_argument("--retry", "-r", type=int, default=0, metavar="N",
                        help="Retry failed connections up to N extra times (default: 0). "
                             "E.g. --retry 2 means up to 3 total attempts.")
    parser.add_argument("--top",           type=int, default=20,
                        help="Number of locations for 'best' mode (default 20)")
    parser.add_argument("--from-last-scan", action="store_true",
                        help="Use locations from the most recent scan output")
    parser.add_argument("--no-quality",     action="store_true",
                        help="Skip quality tests in 'auto' mode")
    parser.add_argument("--protocol", "-p", default="Auto",
                        help="Protocol label to log (does not change ExpressVPN setting)")

    args = parser.parse_args()

    timeout_label = "no limit" if args.timeout == -1 else f"{args.timeout}s"
    print(BANNER)
    print(f"  Mode    : {args.mode}")
    print(f"  Timeout : {timeout_label}"
          + (f"   |   Retry: {args.retry}x" if args.retry > 0 else ""))
    print(f"  Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    vpn     = VPNManager(CLI_PATH)
    history = HistoryManager(Path("."))
    tester  = QualityTester()

    # ── best ──────────────────────────────────────────────────────────────────
    if args.mode == "best":
        mode_best(history, args.top)
        return

    # ── test ──────────────────────────────────────────────────────────────────
    if args.mode == "test":
        if args.from_last_scan:
            locs = load_last_scan()
        elif args.location:
            locs = [args.location]
        else:
            parser.error("Provide a location name or use --from-last-scan")

        if args.filter:
            locs = [l for l in locs if args.filter.lower() in l.lower()]

        if not locs:
            print("❌  No locations to test.")
            return

        qr = mode_test(vpn, tester, history, locs, args.protocol,
                       timeout=args.timeout, retry=args.retry)
        if qr:
            save_quality(qr)
            print_quality_table(qr)
        return

    # ── scan ──────────────────────────────────────────────────────────────────
    if args.mode == "scan":
        sr = mode_scan(vpn, history, args.filter, args.timeout, args.protocol,
                       retry=args.retry)
        if sr:
            save_scan(sr)
        return

    # ── auto ──────────────────────────────────────────────────────────────────
    if args.mode == "auto":
        sr = mode_scan(vpn, history, args.filter, args.timeout, args.protocol,
                       retry=args.retry)
        if sr:
            save_scan(sr)

            if not args.no_quality and sr:
                print(f"\n{'='*58}")
                print(f"  Quality-testing {len(sr)} working location(s) ...")
                locs = [r.location for r in sr]
                qr   = mode_test(vpn, tester, history, locs, args.protocol,
                                 timeout=args.timeout, retry=args.retry)
                if qr:
                    save_quality(qr)
                    print_quality_table(qr)


if __name__ == "__main__":
    main()
