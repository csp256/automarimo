@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "AUTOMARIMO=%SCRIPT_DIR%automarimo.py"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%AUTOMARIMO%" %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%AUTOMARIMO%" %*
    exit /b %errorlevel%
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    python3 "%AUTOMARIMO%" %*
    exit /b %errorlevel%
)

where uv >nul 2>nul
if %errorlevel%==0 (
    uv run "%AUTOMARIMO%" %*
    exit /b %errorlevel%
)

echo Python or uv was not found. Please install Python 3.11+ or 'uv' first.
pause
exit /b 1