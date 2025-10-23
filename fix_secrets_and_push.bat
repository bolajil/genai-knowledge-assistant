@echo off
echo ============================================================
echo Fixing Secrets Issue and Pushing to GitHub
echo ============================================================
echo.

echo ISSUE: GitHub detected API keys in .streamlit/secrets.toml
echo SOLUTION: Remove secrets file from git and update .gitignore
echo.

echo Step 1: Adding .streamlit/secrets.toml to .gitignore...
echo. >> .gitignore
echo # Streamlit secrets (contains API keys) >> .gitignore
echo .streamlit/secrets.toml >> .gitignore
echo .streamlit/ >> .gitignore
echo ✅ Updated .gitignore
echo.

echo Step 2: Removing secrets file from git history...
git rm --cached .streamlit/secrets.toml 2>nul
if errorlevel 1 (
    echo Note: File may not be in git index yet
) else (
    echo ✅ Removed from git index
)
echo.

echo Step 3: Committing the fix...
git add .gitignore
git commit -m "Security fix: Remove API keys from git tracking

- Added .streamlit/secrets.toml to .gitignore
- Removed secrets file from git index
- API keys will no longer be tracked"

if errorlevel 1 (
    echo Note: Nothing to commit or already committed
)
echo.

echo Step 4: Pulling latest changes from GitHub...
git pull origin master --rebase
if errorlevel 1 (
    echo Warning: Pull failed or conflicts detected
    echo You may need to resolve conflicts manually
    pause
)
echo.

echo Step 5: Pushing to GitHub (master branch)...
git push origin master
if errorlevel 1 (
    echo.
    echo ERROR: Push still failed
    echo.
    echo This might be because:
    echo 1. The secrets are still in git history
    echo 2. You need to allow the push on GitHub
    echo.
    echo OPTION 1 - Allow on GitHub (Easiest):
    echo Visit these URLs to allow the secrets:
    echo https://github.com/bolajil/genai-knowledge-assistant/security/secret-scanning/unblock-secret/33bpWiszUH8z8twOijSa7dKcPgV
    echo https://github.com/bolajil/genai-knowledge-assistant/security/secret-scanning/unblock-secret/33bpWkx29ymYn9UjmIYCTomrLw7
    echo.
    echo After allowing, run: git push origin master
    echo.
    echo OPTION 2 - Remove from history (Advanced):
    echo Run: git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .streamlit/secrets.toml" --prune-empty --tag-name-filter cat -- --all
    echo Then: git push origin master --force
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ SUCCESS! Changes pushed to GitHub
echo ============================================================
echo.
echo Your repository: https://github.com/bolajil/genai-knowledge-assistant
echo.
echo IMPORTANT SECURITY NOTE:
echo - .streamlit/secrets.toml is now in .gitignore
echo - Future changes to this file will NOT be tracked
echo - Your API keys are safe
echo.
echo RECOMMENDATION:
echo - Rotate your API keys on OpenAI and Anthropic dashboards
echo - Update your local .streamlit/secrets.toml with new keys
echo - The new keys will not be pushed to GitHub
echo.
pause
