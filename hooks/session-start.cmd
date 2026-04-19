@echo off
REM Gemini CLI SessionStart Hook Wrapper (Windows CMD)
REM Receives JSON on stdin, returns JSON on stdout

SET SCRIPT_DIR=%~dp0

REM Check for PowerShell (most reliable for JSON handling on Windows)
where powershell >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%session-start.ps1"
) ELSE (
    REM Very basic fallback if no PS (unlikely on modern Windows)
    echo {"systemMessage": "Flow detected. Windows native hook active (limited)."}
)
