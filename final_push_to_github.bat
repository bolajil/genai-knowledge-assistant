@echo off
echo ============================================================
echo Final Push to GitHub - Handling All Issues
echo ============================================================
echo.

echo Step 1: Stashing any unstaged changes...
git stash
echo.

echo Step 2: Pulling latest changes from GitHub...
git pull origin master --no-rebase
if errorlevel 1 (
    echo.
    echo Pull failed. Trying with rebase...
    git pull origin master --rebase
    if errorlevel 1 (
        echo.
        echo ERROR: Cannot pull. You may have conflicts.
        echo.
        echo Manual steps needed:
        echo 1. Run: git status
        echo 2. Resolve any conflicts
        echo 3. Run: git add .
        echo 4. Run: git rebase --continue
        echo 5. Run: git push origin master
        echo.
        pause
        exit /b 1
    )
)
echo ✅ Pulled successfully
echo.

echo Step 3: Applying stashed changes back...
git stash pop
if errorlevel 1 (
    echo Note: No stash to apply or conflicts in stash
)
echo.

echo Step 4: Adding all changes...
git add .
echo ✅ Changes staged
echo.

echo Step 5: Committing if there are changes...
git commit -m "Merge and sync with remote" 2>nul
if errorlevel 1 (
    echo Note: No new changes to commit
)
echo.

echo Step 6: Pushing to GitHub...
git push origin master
if errorlevel 1 (
    echo.
    echo ============================================================
    echo Push still blocked - Using GitHub's Allow Feature
    echo ============================================================
    echo.
    echo The push is blocked because of API keys in git history.
    echo.
    echo EASIEST SOLUTION:
    echo.
    echo 1. Visit these URLs to allow the secrets:
    echo.
    echo    OpenAI Key:
    echo    https://github.com/bolajil/genai-knowledge-assistant/security/secret-scanning/unblock-secret/33bpWiszUH8z8twOijSa7dKcPgV
    echo.
    echo    Anthropic Key:
    echo    https://github.com/bolajil/genai-knowledge-assistant/security/secret-scanning/unblock-secret/33bpWkx29ymYn9UjmIYCTomrLw7
    echo.
    echo 2. Click "Allow secret" on each page
    echo.
    echo 3. Then run: git push origin master
    echo.
    echo ============================================================
    echo.
    echo ALTERNATIVE: Force push (removes API keys from history)
    echo.
    echo WARNING: This rewrites git history. Only use if you're sure.
    echo.
    echo Run these commands:
    echo   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .streamlit/secrets.toml" HEAD
    echo   git push origin master --force
    echo.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ SUCCESS! Pushed to GitHub
echo ============================================================
echo.
echo Your repository: https://github.com/bolajil/genai-knowledge-assistant
echo.
echo IMPORTANT:
echo - Your cleanup is now on GitHub
echo - .streamlit/secrets.toml is in .gitignore
echo - Consider rotating your API keys for security
echo.
pause
