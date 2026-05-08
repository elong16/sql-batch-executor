@echo off
cd /d D:\pythonProject\sql-batch-executor
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    py main.py
)
echo Exit code: %ERRORLEVEL%
pause
