@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: ── Admin elevation ──────────────────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ── Dependency check ─────────────────────────────────────────────────────────
python -c "import requests" >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [INFO] Installing 'requests' library for speed tests...
    pip install requests --quiet
)

:MENU
cls
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║          E X P R E S S F I N D E R          ║
echo  ║              VPN Location Tool               ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo   [1]  Fast Scan  — ALL locations  (history-sorted)
echo   [2]  Fast Scan  — USA only
echo   [3]  Fast Scan  — custom filter
echo   [4]  Fast Scan  — faster timeout (12s, more misses)
echo   ─────────────────────────────────────────────
echo   [5]  Quality Test — from last scan results
echo   [6]  Quality Test — single location
echo   ─────────────────────────────────────────────
echo   [7]  Auto mode  — Scan ALL then quality test
echo   [8]  Auto mode  — USA scan then quality test
echo   ─────────────────────────────────────────────
echo   [9]  Show best locations  (from history)
echo   [0]  Exit
echo.
set /p CHOICE=  Choose [0-9]:

if "%CHOICE%"=="1" goto SCAN_ALL
if "%CHOICE%"=="2" goto SCAN_USA
if "%CHOICE%"=="3" goto SCAN_FILTER
if "%CHOICE%"=="4" goto SCAN_FAST
if "%CHOICE%"=="5" goto TEST_LAST
if "%CHOICE%"=="6" goto TEST_ONE
if "%CHOICE%"=="7" goto AUTO_ALL
if "%CHOICE%"=="8" goto AUTO_USA
if "%CHOICE%"=="9" goto BEST
if "%CHOICE%"=="0" goto END
goto MENU

:: ────────────────────────────────────────────────────────────────────────────

:SCAN_ALL
echo.
echo  Scanning ALL locations (timeout 18s each) ...
echo.
python expressfinder.py scan
goto DONE

:SCAN_USA
echo.
echo  Scanning USA locations only ...
echo.
python expressfinder.py scan --filter USA
goto DONE

:SCAN_FILTER
echo.
set /p KW=  Enter filter keyword (e.g. UK, Japan, Canada):
python expressfinder.py scan --filter "%KW%"
goto DONE

:SCAN_FAST
echo.
echo  Fast scan (12s timeout — may miss slow-to-connect servers) ...
echo.
python expressfinder.py scan --timeout 12
goto DONE

:TEST_LAST
echo.
echo  Quality-testing locations from last scan ...
echo.
python expressfinder.py test --from-last-scan
goto DONE

:TEST_ONE
echo.
set /p LOC=  Enter exact location name (e.g. USA - New York):
python expressfinder.py test "%LOC%"
goto DONE

:AUTO_ALL
echo.
echo  Auto: scanning ALL then quality-testing working locations ...
echo.
python expressfinder.py auto
goto DONE

:AUTO_USA
echo.
echo  Auto: scanning USA then quality-testing working locations ...
echo.
python expressfinder.py auto --filter USA
goto DONE

:BEST
echo.
python expressfinder.py best --top 30
goto DONE

:: ────────────────────────────────────────────────────────────────────────────

:DONE
echo.
echo ─────────────────────────────────────────────────
echo  Done. Results saved in the 'results\' folder.
echo ─────────────────────────────────────────────────
echo.
set /p BACK=  Press Enter to return to menu, or Ctrl+C to exit...
goto MENU

:END
echo  Bye!
endlocal
