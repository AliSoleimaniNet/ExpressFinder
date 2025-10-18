ExpressFinder
ExpressFinder provides two Python scripts to interact with the ExpressVPN CLI on Windows:

test.py: Tests connections to all ExpressVPN locations (excluding Israel) using LightwayUdp and LightwayTcp protocols, logging successful connections to successful_connections.txt.
connect.py: Attempts to connect to ExpressVPN locations using LightwayUdp until a successful connection is made, then stops.

Batch files (test.bat and connect.bat) ensure scripts run with administrator privileges.
Features

Test Script: Tests all ExpressVPN locations, logs successful connections (location, protocol, time) to a file.
Connect Script: Connects to a location and stops upon success, maintaining the connection.
Automatic elevation via batch files.

Prerequisites

Python 3.x:
Install from python.org.
Add Python to PATH or set the PYTHON variable in batch files (e.g., C:\Python39\python.exe).


ExpressVPN:
Install ExpressVPN on Windows.
Ensure CLI is at C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe. Update EXPRESSVPN_CLI in scripts if different.


Administrator Privileges:
Required for CLI interaction. Batch files handle elevation.


Dependencies:
Uses standard Python libraries (subprocess, time, shlex, sys, re). No extra packages needed.



Installation

Clone the repository:git clone https://github.com/gameraliaz/ExpressFinder.git


Navigate to the directory:cd ExpressFinder


Verify Python and ExpressVPN installation.
Update EXPRESSVPN_CLI in test.py and connect.py if needed.
(Optional) Set PYTHON in test.bat and connect.bat if Python is not in PATH.

Usage
Run scripts via batch files to ensure administrator privileges.
Before Running

Check CLI Path: Ensure EXPRESSVPN_CLI in scripts matches your ExpressVPN installation path.
Configure Protocols: In connect.py, PROTOCOLS is set to LightwayUdp. Add LightwayTcp to test both.
Modify Location Filter: Remove if "Israel" in loc_name in scripts to include all locations.

Running Test Script (test.py)
Tests all locations and logs results.

Double-click test.bat or run in a command prompt:test.bat


The script:
Fetches ExpressVPN locations.
Tests connections with LightwayUdp and LightwayTcp.
Logs successful connections to successful_connections.txt.
Disconnects after each attempt.


Check successful_connections.txt for results.

Running Connect Script (connect.py)
Connects to a location and stops on success.

Double-click connect.bat or run in a command prompt:connect.bat


The script:
Fetches ExpressVPN locations.
Attempts connections with LightwayUdp until successful.
Maintains the connection and displays status.



Output

Test Script: successful_connections.txt with format:Location, Protocol, TimeToConnectSeconds
USA - New York, LightwayUdp, 4.82


Connect Script: Console output showing connection attempts and status.

Troubleshooting

Python Not Found: Add Python to PATH or update batch files with the full path.
CLI Errors: Verify ExpressVPN installation and CLI path. Ensure the service is running.
No Locations: Check ExpressVPN subscription and CLI output ("C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe" list).
Permission Issues: Right-click batch files and select "Run as administrator".

License
MIT License. See LICENSE file (if included).