@echo off
setlocal
chcp 65001 >nul
title Codex Token Meter - Local Web Dashboard

set "METER_SCRIPT=%~dp0chatgpt_usage.py"
if not exist "%METER_SCRIPT%" (
  echo ERROR: chatgpt_usage.py is not in the same folder.
  pause
  exit /b 2
)

where python.exe >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_EXE=python.exe"
  goto RUN_WEB
)

where python3.exe >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_EXE=python3.exe"
  goto RUN_WEB
)

where py.exe >nul 2>nul
if %errorlevel% equ 0 goto RUN_WEB_WITH_PY

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
  if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
)
if defined PYTHON_EXE goto RUN_WEB

echo ERROR: A Python 3 executable could not be located.
pause
exit /b 1

:RUN_WEB
"%PYTHON_EXE%" "%METER_SCRIPT%" --web %*
set "METER_EXIT=%errorlevel%"
goto FINISH

:RUN_WEB_WITH_PY
py.exe -3 "%METER_SCRIPT%" --web %*
set "METER_EXIT=%errorlevel%"

:FINISH
echo.
echo The local dashboard has stopped.
if "%~1"=="" pause
exit /b %METER_EXIT%
