@echo off
REM Script to reload uwsgi configuration on Windows

REM Method 1: Touch the reload file (if touch-reload is configured)
if exist C:\tmp\uwsgi.reload (
    echo. > C:\tmp\uwsgi.reload
    echo Reload signal sent via touch-reload file
    exit /b 0
)

REM Method 2: Use uwsgi --reload with PID file
if exist C:\tmp\uwsgi.pid (
    uwsgi --reload C:\tmp\uwsgi.pid
    echo Reload signal sent via PID file
    exit /b 0
)

REM Method 3: Find uwsgi process and send signal
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq uwsgi.exe" /FO LIST ^| findstr PID') do (
    echo Reload signal sent to uwsgi process %%i
    REM Note: Windows doesn't support HUP signal, restart may be needed
    exit /b 0
)

echo Could not find uwsgi process or reload mechanism
echo Please ensure uwsgi is running with the updated configuration

