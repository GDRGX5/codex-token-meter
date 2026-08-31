@echo off
setlocal
chcp 65001 >nul
title ChatGPT - Codex Token Meter

set "METER_SCRIPT=%~dp0chatgpt_usage.py"
if not exist "%METER_SCRIPT%" (
  echo ERROR: chatgpt_usage.py is not in the same folder.
  echo Folder: %~dp0
  pause
  exit /b 2
)

where python.exe >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_EXE=python.exe"
  goto RUN_WITH_PYTHON
)

where python3.exe >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_EXE=python3.exe"
  goto RUN_WITH_PYTHON
)

where py.exe >nul 2>nul
if %errorlevel% equ 0 goto RUN_WITH_PY_LAUNCHER

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
  if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
)
if defined PYTHON_EXE goto RUN_WITH_PYTHON

echo ERROR: Python 3 is installed, but its executable could not be located.
pause
exit /b 1

:RUN_WITH_PYTHON
"%PYTHON_EXE%" "%METER_SCRIPT%" %*
set "METER_EXIT=%errorlevel%"
goto FINISH

:RUN_WITH_PY_LAUNCHER
py.exe -3 "%METER_SCRIPT%" %*
set "METER_EXIT=%errorlevel%"

:FINISH
if "%~1"=="" (
  echo.
  pause
)
exit /b %METER_EXIT%
