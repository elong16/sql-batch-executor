@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "REPO=%CD:\=/%"
set "DEFAULT_MESSAGE=Update project %DATE% %TIME:~0,8%"
set "DRY_RUN=0"

if /I "%~1"=="--dry-run" (
    set "DRY_RUN=1"
    shift /1
)

echo [1/4] Checking repository...
git -c safe.directory="%REPO%" rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto not_repo

git -c safe.directory="%REPO%" remote get-url origin >nul 2>nul
if errorlevel 1 goto no_remote

echo [2/4] Current changes:
git -c safe.directory="%REPO%" status --short

git -c safe.directory="%REPO%" diff --quiet
set "HAS_TRACKED=%ERRORLEVEL%"
git -c safe.directory="%REPO%" ls-files --others --exclude-standard --directory | findstr . >nul
set "HAS_UNTRACKED=%ERRORLEVEL%"
if "%HAS_TRACKED%"=="0" if not "%HAS_UNTRACKED%"=="0" goto no_changes

set "COMMIT_MESSAGE=%~1"
if "%COMMIT_MESSAGE%"=="" set "COMMIT_MESSAGE=%DEFAULT_MESSAGE%"

if "%DRY_RUN%"=="1" (
    echo.
    echo Dry run only. Nothing was committed or pushed.
    echo Commit message would be: %COMMIT_MESSAGE%
    exit /b 0
)

echo.
echo [3/4] Committing: %COMMIT_MESSAGE%
git -c safe.directory="%REPO%" add -A
if errorlevel 1 goto failed

git -c safe.directory="%REPO%" commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 goto failed

echo.
echo [4/4] Pushing to GitHub...
git -c safe.directory="%REPO%" push
if errorlevel 1 goto failed

echo.
echo Done.
pause
exit /b 0

:no_changes
echo.
echo No changes to commit.
pause
exit /b 0

:not_repo
echo.
echo This folder is not a Git repository.
pause
exit /b 1

:no_remote
echo.
echo Git remote origin is not configured.
pause
exit /b 1

:failed
echo.
echo Git submit failed. Check the error above.
pause
exit /b 1
