@echo off
where python >nul 2>nul
if %errorlevel% equ 0 (
  python "%~dp0chatgpt_usage.py" %*
  exit /b
)
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 "%~dp0chatgpt_usage.py" %*
  exit /b
)
echo Error: Python 3 was not found.
exit /b 1
