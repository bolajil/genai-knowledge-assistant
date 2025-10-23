@echo off
echo ============================================================
echo Pushing Project Cleanup to GitHub (bolajil)
echo ============================================================
echo.

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

echo Step 1: Checking current git status...
git status
echo.

echo Step 2: Adding all changes (respects .gitignore)...
git add .
if errorlevel 1 (
    echo ERROR: Failed to add files
    pause
    exit /b 1
)
echo ✅ Files staged successfully
echo.

echo Step 3: Committing changes...
git commit -m "Project cleanup: Archived 69 non-essential files

- Moved debug files (12) to archive
- Moved fix/patch files (19) to archive
- Moved temporary files (18) to archive
- Moved test files (16) to archive
- Moved duplicate startup scripts (7) to archive
- Updated .gitignore to exclude archives
- Created cleanup documentation
- Added P0 critical fixes and Redis integration
- All core application files preserved
- System tested and verified working"

if errorlevel 1 (
    echo.
    echo Note: If no changes to commit, that's okay - files may already be committed
    echo.
)
echo.

echo Step 4: Pushing to GitHub...
echo Attempting to push to origin main...
git push origin main
if errorlevel 1 (
    echo.
    echo Push to 'main' failed. Trying 'master' branch...
    git push origin master
    if errorlevel 1 (
        echo.
        echo ERROR: Push failed for both main and master branches
        echo.
        echo Possible solutions:
        echo 1. Check if remote 'origin' is configured: git remote -v
        echo 2. Set up remote if missing: git remote add origin https://github.com/bolajil/genai-knowledge-assistant.git
        echo 3. Check your GitHub credentials
        echo 4. Try: git push -u origin main
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo ✅ SUCCESS! Changes pushed to GitHub
echo ============================================================
echo.
echo Your repository: https://github.com/bolajil/genai-knowledge-assistant
echo.
echo What was pushed:
echo   ✅ Updated .gitignore
echo   ✅ Cleanup documentation
echo   ✅ All source code changes
echo   ✅ P0 fixes and improvements
echo.
echo What was NOT pushed (excluded by .gitignore):
echo   ❌ archive_cleanup_2024/ directory
echo   ❌ Cleanup scripts
echo   ❌ .env files
echo   ❌ data/ directory
echo.
echo Next steps:
echo 1. Visit https://github.com/bolajil/genai-knowledge-assistant to verify
echo 2. After 1-2 weeks of testing, you can delete the local archive:
echo    rmdir /s /q archive_cleanup_2024
echo.
pause
