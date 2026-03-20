@echo off
setlocal
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%~dp0automarimo.py" %*
    exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0automarimo.py" %*
    exit /b %ERRORLEVEL%
)
echo Python was not found. Please install Python 3.11+ first.
pause
exit /b 1
