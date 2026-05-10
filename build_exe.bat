@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo [1/3] Installing runtime dependencies...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto failed

echo [2/3] Installing build dependencies...
"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed

echo [3/3] Building exe...
"%PYTHON%" scripts\build_exe.py
if errorlevel 1 goto failed

echo.
echo Build finished. Check the dist folder for the generated EXE.
pause
exit /b 0

:failed
echo.
echo Build failed. Check the error above.
pause
exit /b 1
