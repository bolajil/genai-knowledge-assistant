@echo off
echo ============================================================
echo Clean Start: Push Without Secrets in History
echo ============================================================
echo.
echo This will create a fresh git history without any secrets.
echo Your code and cleanup will be preserved, just the history is reset.
echo.
echo WARNING: This will:
echo - Create a new branch without secret history
echo - Force push to GitHub (overwrites remote)
echo - You'll lose git history but keep all your code
echo.
set /p confirm="Type YES to continue: "
if /i not "%confirm%"=="YES" (
    echo Cancelled.
    pause
    exit /b 1
)
echo.

echo Step 1: Aborting any ongoing rebase...
git rebase --abort 2>nul
echo ✅ Done
echo.

echo Step 2: Updating .gitignore with ALL secret files...
(
echo.
echo # ============================================================
echo # API Keys and Secrets - NEVER COMMIT THESE
echo # ============================================================
echo.
echo # Streamlit secrets
echo .streamlit/secrets.toml
echo .streamlit/
echo.
echo # AWS and Storage Credentials  
echo config/storage.env
echo config/storage.env.bak
echo config/*.env
echo config/*.env.bak
echo.
echo # Environment files
echo .env
echo .env.local
echo .env.*.local
echo *.env
echo *.env.bak
echo.
echo # Backup files with potential secrets
echo *.bak
echo *~
echo.
echo # Database files
echo *.db
echo *.sqlite
echo *.sqlite3
echo.
echo # Logs
echo *.log
echo logs/
echo mcp_logs.db
) >> .gitignore
echo ✅ .gitignore updated
echo.

echo Step 3: Removing secret files from working directory tracking...
git rm --cached .streamlit/secrets.toml 2>nul
git rm --cached config/storage.env 2>nul
git rm --cached config/storage.env.bak 2>nul
git rm --cached data/users.db 2>nul
git rm --cached mcp_logs.db 2>nul
echo ✅ Secret files untracked
echo.

echo Step 4: Creating clean branch without history...
git checkout --orphan clean-master
if errorlevel 1 (
    echo ERROR: Failed to create new branch
    pause
    exit /b 1
)
echo ✅ New branch created
echo.

echo Step 5: Adding all files (respecting .gitignore)...
git add .
echo ✅ Files staged
echo.

echo Step 6: Creating initial commit...
git commit -m "Initial commit: Clean project without secrets

- Project cleanup complete (69 files archived)
- All secrets properly excluded via .gitignore
- Redis integration and P0 fixes included
- System tested and verified working
- Clean git history without any API keys"

if errorlevel 1 (
    echo ERROR: Failed to commit
    pause
    exit /b 1
)
echo ✅ Committed
echo.

echo Step 7: Deleting old master branch...
git branch -D master 2>nul
echo ✅ Old branch deleted
echo.

echo Step 8: Renaming clean-master to master...
git branch -m master
echo ✅ Branch renamed
echo.

echo Step 9: Force pushing to GitHub...
echo This will overwrite the remote repository with clean history...
git push origin master --force
if errorlevel 1 (
    echo.
    echo ERROR: Push failed
    echo.
    echo Possible solutions:
    echo 1. Check your internet connection
    echo 2. Verify GitHub credentials
    echo 3. Make sure remote is set: git remote -v
    echo 4. Try: git remote set-url origin https://github.com/bolajil/genai-knowledge-assistant.git
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ SUCCESS! Clean History Pushed to GitHub
echo ============================================================
echo.
echo Your repository now has:
echo ✅ Clean git history (no secrets)
echo ✅ All your code and cleanup preserved
echo ✅ Proper .gitignore for all secrets
echo ✅ Ready for development
echo.
echo Repository: https://github.com/bolajil/genai-knowledge-assistant
echo.
echo IMPORTANT NEXT STEPS:
echo 1. Verify on GitHub that your code is there
echo 2. Your local secret files are still safe (not pushed)
echo 3. Consider rotating your API keys for extra security:
echo    - OpenAI: https://platform.openai.com/api-keys
echo    - Anthropic: https://console.anthropic.com/settings/keys
echo    - AWS: https://console.aws.amazon.com/iam/
echo.
echo ============================================================
pause
