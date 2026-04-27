@echo off
REM Windows wrapper for the Flow session-start hook.
REM Locates Git Bash and delegates to session-start.sh. All real logic lives in the POSIX script.
setlocal
set "BASH_EXE="
if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not defined BASH_EXE for /f "delims=" %%i in ('where bash 2^>nul') do if not defined BASH_EXE set "BASH_EXE=%%i"
if not defined BASH_EXE (
  1>&2 echo {"systemMessage":"Flow hook skipped: Git Bash not found on Windows."}
  exit /b 0
)
"%BASH_EXE%" "%~dp0session-start.sh" %*
