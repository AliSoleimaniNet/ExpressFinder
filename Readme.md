# ExpressFinder

ExpressFinder provides two Python scripts to interact with the ExpressVPN CLI on Windows:
- `test.py`: Tests connections to all ExpressVPN locations (excluding Israel) using LightwayUdp and LightwayTcp protocols, logging successful connections to `successful_connections.txt`.
- `connect.py`: Attempts to connect to ExpressVPN locations using LightwayUdp until a successful connection is made, then stops.

Batch files (`test.bat` and `connect.bat`) ensure scripts run with administrator privileges.

## Features
- **Test Script**: Tests all ExpressVPN locations, logs successful connections (location, protocol, time) to a file.
- **Connect Script**: Connects to a location and stops upon success, maintaining the connection.
- Automatic elevation via batch files.

## Prerequisites
1. **Python 3.x**:
   - Install from [python.org](https://www.python.org/downloads/).
   - Add Python to PATH or set the `PYTHON` variable in batch files (e.g., `C:\Python39\python.exe`).
2. **ExpressVPN**:
   - Install ExpressVPN on Windows.
   - Ensure CLI is at `C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe`. Update `EXPRESSVPN_CLI` in scripts if different.
3. **Administrator Privileges**:
   - Required for CLI interaction. Batch files handle elevation.
4. **Dependencies**:
   - Uses standard Python libraries (`subprocess`, `time`, `shlex`, `sys`, `re`). No extra packages needed.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/gameraliaz/ExpressFinder.git
   ```
2. Navigate to the directory:
   ```bash
   cd ExpressFinder
   ```
3. Verify Python and ExpressVPN installation.
4. Update `EXPRESSVPN_CLI` in `test.py` and `connect.py` if needed.
5. (Optional) Set `PYTHON` in `test.bat` and `connect.bat` if Python is not in PATH.

## Usage
Run scripts via batch files to ensure administrator privileges.

### Before Running
- **Check CLI Path**: Ensure `EXPRESSVPN_CLI` in scripts matches your ExpressVPN installation path.
- **Configure Protocols**: In `connect.py`, `PROTOCOLS` is set to `LightwayUdp`. Add `LightwayTcp` to test both.
- **Modify Location Filter**: Remove `if "Israel" in loc_name` in scripts to include all locations.

### Running Test Script (`test.py`)
Tests all locations and logs results.
1. Double-click `test.bat` or run in a command prompt:
   ```bash
   test.bat
   ```
2. The script:
   - Fetches ExpressVPN locations.
   - Tests connections with LightwayUdp and LightwayTcp.
   - Logs successful connections to `successful_connections.txt`.
   - Disconnects after each attempt.
3. Check `successful_connections.txt` for results.

### Running Connect Script (`connect.py`)
Connects to a location and stops on success.
1. Double-click `connect.bat` or run in a command prompt:
   ```bash
   connect.bat
   ```
2. The script:
   - Fetches ExpressVPN locations.
   - Attempts connections with LightwayUdp until successful.
   - Maintains the connection and displays status.

## Output
- **Test Script**: `successful_connections.txt` with format:
  ```
  Location, Protocol, TimeToConnectSeconds
  USA - New York, LightwayUdp, 4.82
  ```
- **Connect Script**: Console output showing connection attempts and status.

## Troubleshooting
- **Python Not Found**: Add Python to PATH or update batch files with the full path.
- **CLI Errors**: Verify ExpressVPN installation and CLI path. Ensure the service is running.
- **No Locations**: Check ExpressVPN subscription and CLI output (`"C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe" list`).
- **Permission Issues**: Right-click batch files and select "Run as administrator".