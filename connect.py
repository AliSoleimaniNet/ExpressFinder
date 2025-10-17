import subprocess
import time
import shlex
import sys
import re

EXPRESSVPN_CLI = r'C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe'
PROTOCOLS =["LightwayUdp "]#= ["LightwayUdp ", "LightwayTcp "]

def run_command(cmd):
    """Run a command and return its output or error as string."""
    try:
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
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
    # Extract lines with format: Location Name (possibly with spaces) + ID number at the end
    match = re.match(r'^(.+?)\s+(\d+)$', line)
    if match:
        loc_name = match.group(1).strip()
        loc_id = match.group(2).strip()
        locations.append(loc_name)

if not locations:
    print("❌ Could not find any VPN locations.")
    sys.exit(1)

print(f"✅ Found {len(locations)} VPN locations.")

# Step 2️⃣: Try connecting with each protocol for each location
connected = False

for loc in locations:
    for proto in PROTOCOLS:
        print(f"\n🔷 Setting protocol to '{proto}'...")
        out_protocol = run_command(f'"{EXPRESSVPN_CLI}" protocol {proto}')
        print(out_protocol)

        print(f"🔷 Connecting to '{loc}'...")
        out_connect = run_command(f'"{EXPRESSVPN_CLI}" connect "{loc}"')
        print(out_connect)

        out_status = run_command(f'"{EXPRESSVPN_CLI}" status')
        print(f"📋 Connection status: {out_status}")

        if "Connected" in out_status or "متصل" in out_status:
            print(f"\n✅ Successfully connected to '{loc}' using protocol '{proto}'.")
            connected = True
            break  # Exit protocol loop
    if connected:
        break  # Exit location loop

if not connected:
    print("\n❌ No successful connection found with any location or protocol.")
else:
    print("\n🎯 Script finished. VPN remains connected.")
