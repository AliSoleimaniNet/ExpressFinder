import subprocess
import time
import shlex
import sys
import re

EXPRESSVPN_CLI = r'C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe'
PROTOCOLS      = ["Auto"]
OUTPUT_FILE    = "successful_connections.txt"
CONNECT_TIMEOUT   = 20   # seconds — was None (could hang forever!)
DISCONNECT_TIMEOUT = 8   # seconds
LIST_TIMEOUT       = 15  # seconds

# ──────────────────────────────────────────────
def run_command(cmd, timeout=10):
    """Run a CLI command, return combined stdout+stderr."""
    try:
        r = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)

def is_connected(output: str) -> bool:
    return "Connected" in output or "متصل" in output

# ── 1. Fetch locations ─────────────────────────
print("📋 Fetching VPN locations list...")
list_output = run_command(f'"{EXPRESSVPN_CLI}" list', timeout=LIST_TIMEOUT)

locations = []
for line in list_output.splitlines():
    line = line.strip()
    if not line or line.endswith(':'):
        continue
    match = re.match(r'^(.+?)\s+(\d+)$', line)
    if match:
        name = match.group(1).strip()
        if "israel" in name.lower():
            continue
        locations.append(name)

# Filter: USA only
targets = [loc for loc in locations if "USA" in loc]

if not targets:
    print("❌ No USA VPN locations found.")
    sys.exit(1)

print(f"✅ Found {len(targets)} USA locations to scan.\n")

# ── 2. Scan ────────────────────────────────────
results   = []   # (loc, proto, elapsed)
success   = 0
failed    = 0
timed_out = 0
total     = len(targets)

for i, loc in enumerate(targets, 1):
    for proto in PROTOCOLS:
        label = f"[{i:>3}/{total}]"
        print(f"{label} ⏳ {loc} ... ", end="", flush=True)

        start = time.time()
        out   = run_command(f'"{EXPRESSVPN_CLI}" connect "{loc}"',
                            timeout=CONNECT_TIMEOUT)
        elapsed = round(time.time() - start, 2)

        if "TIMEOUT" in out:
            print(f"⏳ timed out ({CONNECT_TIMEOUT}s)")
            timed_out += 1
        elif is_connected(out):
            print(f"✅ connected in {elapsed}s")
            results.append((loc, proto, elapsed))
            success += 1
        else:
            print(f"❌ failed")
            failed += 1

        # Disconnect quickly before next attempt
        run_command(f'"{EXPRESSVPN_CLI}" disconnect',
                    timeout=DISCONNECT_TIMEOUT)

# ── 3. Write results ───────────────────────────
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("Location, Protocol, TimeToConnectSeconds\n")
    for loc, proto, elapsed in results:
        f.write(f"{loc}, {proto}, {elapsed}\n")

# ── 4. Summary ─────────────────────────────────
print(f"\n{'─'*50}")
print(f"🎯 Scan complete!")
print(f"   ✅ Connected : {success}")
print(f"   ❌ Failed    : {failed}")
print(f"   ⏳ Timed out : {timed_out}")
print(f"   📄 Results   : {OUTPUT_FILE}")
print(f"{'─'*50}")
