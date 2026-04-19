@echo off
REM Windows CMD hook runner for Flow
REM Detects if bash is available and runs the bash version, or provides a native fallback

SET HOOK_NAME=%1
SET SCRIPT_DIR=%~dp0

IF "%HOOK_NAME%"=="" (
    echo {"error": "No hook name provided"} >&2
    exit /b 1
)

REM Check for git bash or WSL bash
where bash >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    bash "%SCRIPT_DIR%run-hook.sh" %HOOK_NAME%
) ELSE (
    REM Native Windows fallback (limited support)
    IF EXIST "%SCRIPT_DIR%%HOOK_NAME%.ps1" (
        powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%%HOOK_NAME%.ps1"
    ) ELSE (
        echo {"error": "No bash found and no native Windows hook for %HOOK_NAME%"} >&2
        exit /b 1
    )
)
