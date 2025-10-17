import subprocess
import time
import shlex
import sys
import re

EXPRESSVPN_CLI = r'C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe'
PROTOCOLS = ["LightwayUdp", "LightwayTcp"]
OUTPUT_FILE = "successful_connections.txt"

def run_command(cmd, timeout=None):
    """Run a command with optional timeout, return stdout or error."""
    try:
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"⏳ Command timed out after {timeout} seconds."
    except Exception as e:
        return str(e)

# Step 1️⃣: Get locations list
print("📋 Fetching VPN locations list...")
list_output = run_command(f'"{EXPRESSVPN_CLI}" list')

locations = []
for line in list_output.splitlines():
    line = line.strip()
    if not line or line.endswith(':'):
        continue  # Skip empty lines or section titles
    match = re.match(r'^(.+?)\s+(\d+)$', line)
    if match:
        loc_name = match.group(1).strip()
        if "Israel" in loc_name or "israel" in loc_name: continue
        locations.append(loc_name)

if not locations:
    print("❌ Could not find any VPN locations.")
    sys.exit(1)

print(f"✅ Found {len(locations)} VPN locations.")

# Prepare output file
with open(OUTPUT_FILE, "w") as f:
    f.write("Location, Protocol, TimeToConnectSeconds\n")

# Step 2️⃣: Try connecting
for loc in locations:
    for proto in PROTOCOLS:
        print(f"\n🔷 Setting protocol to '{proto}'...")
        out_protocol = run_command(f'"{EXPRESSVPN_CLI}" protocol {proto}')
        print(out_protocol)

        print(f"🔷 Connecting to '{loc}' with protocol '{proto}'...")
        start_time = time.time()
        out_connect = run_command(f'"{EXPRESSVPN_CLI}" connect "{loc}"', timeout=None)
        end_time = time.time()

        elapsed = round(end_time - start_time, 2)
        print(out_connect)

        out_status = run_command(f'"{EXPRESSVPN_CLI}" status')
        print(f"📋 Connection status: {out_status}")

        if "Connected" in out_status or "متصل" in out_status:
            print(f"✅ Connected to '{loc}' using '{proto}' in {elapsed} seconds.")
            with open(OUTPUT_FILE, "a") as f:
                f.write(f"{loc}, {proto}, {elapsed}\n")
        else:
            print(f"❌ Failed to connect to '{loc}' using '{proto}'.")

        print("🔷 Disconnecting...")
        out_disconnect = run_command(f'"{EXPRESSVPN_CLI}" disconnect')
        print(out_disconnect)

print("\n🎯 Script finished. Successful connections (if any) are saved in:")
print(OUTPUT_FILE)
