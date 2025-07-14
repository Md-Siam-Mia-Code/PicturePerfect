@echo off
setlocal

:: =================================================================================
:: == PicturePerfect - Auto-Start Setup Script
:: =================================================================================
:: This script will:
:: 1. Request Administrator privileges.
:: 2. Create a silent launcher (VBScript) and a logic launcher (batch file).
:: 3. Create a Windows Task Scheduler task to run PicturePerfect on user logon.
:: =================================================================================

title PicturePerfect Auto-Start Setup

:: --- Step 1: Request Administrator Privileges ---
ECHO [*] Checking for Administrator privileges...
net session >nul 2>&1
IF %errorlevel% NEQ 0 (
    ECHO [!] Administrator privileges required. Please re-run this script as an Administrator.
    ECHO     Right-click 'auto_start.bat' and select 'Run as administrator'.
    PAUSE
    EXIT /B
)
ECHO [+] Administrator privileges detected.

:: --- Step 2: Create the Silent VBScript Launcher ---
ECHO [*] Creating silent launcher script (run_silent.vbs)...
SET "VBS_SCRIPT=%~dp0run_silent.vbs"
SET "LAUNCH_SCRIPT=%~dp0launch_app.bat"

ECHO Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
ECHO WshShell.Run """" & "%LAUNCH_SCRIPT%" & """", 0, False >> "%VBS_SCRIPT%"

IF EXIST "%VBS_SCRIPT%" (
    ECHO [+] Silent launcher created successfully.
) ELSE (
    ECHO [!] ERROR: Failed to create silent launcher script.
    PAUSE
    EXIT /B 1
)

:: --- Step 3: Create the Scheduled Task ---
ECHO [*] Creating scheduled task 'PicturePerfect_AutoStart' to run on user logon...
schtasks /Create /TN "PicturePerfect_AutoStart" /TR "'%VBS_SCRIPT%'" /SC ONLOGON /RL HIGHEST /F >nul

IF %errorlevel% == 0 (
    ECHO [+] Scheduled task created successfully!
) ELSE (
    ECHO [!] ERROR: Failed to create the scheduled task. Errorlevel: %errorlevel%
    PAUSE
    EXIT /B 1
)

:: --- Step 4: Run the task instantly for the first time ---
ECHO [*] Performing an initial background launch of PicturePerfect...
schtasks /Run /TN "PicturePerfect_AutoStart"

ECHO.
ECHO =================================================================================
ECHO  ✅ SETUP COMPLETE!
ECHO =================================================================================
ECHO.
ECHO PicturePerfect is now configured to start automatically and silently
ECHO whenever you log into Windows.
ECHO.
ECHO You can manage this task in the Windows 'Task Scheduler'.
ECHO.
PAUSE