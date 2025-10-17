@echo off
:: Your Python script filename
set SCRIPT=test.py

:: Full path to python (if python is in PATH, no need to set this)
set PYTHON=python

:: Ensure running in the script's current directory
cd /d %~dp0

:: Auto-run as administrator
:: If not running as admin, re-launch this script with admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo Running Python script with administrator privileges...
%PYTHON% %SCRIPT%

pause
