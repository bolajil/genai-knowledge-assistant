@echo off
echo ============================================================
echo Remove ALL Secrets from Git History
echo ============================================================
echo.
echo This will:
echo 1. Abort current rebase
echo 2. Update .gitignore with all secret files
echo 3. Remove secrets from git history using BFG Repo Cleaner
echo 4. Push clean history to GitHub
echo.
pause

echo Step 1: Aborting any ongoing rebase...
git rebase --abort 2>nul
echo ✅ Rebase aborted
echo.

echo Step 2: Updating .gitignore with all secret files...
(
echo.
echo # API Keys and Secrets
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
) >> .gitignore
echo ✅ .gitignore updated
echo.

echo Step 3: Removing secret files from git tracking...
git rm --cached .streamlit/secrets.toml 2>nul
git rm --cached config/storage.env 2>nul
git rm --cached config/storage.env.bak 2>nul
echo ✅ Files removed from git index
echo.

echo Step 4: Committing .gitignore changes...
git add .gitignore
git commit -m "Security: Add all secret files to .gitignore"
echo ✅ Committed
echo.

echo ============================================================
echo IMPORTANT: Removing secrets from git history
echo ============================================================
echo.
echo We need to use BFG Repo Cleaner to remove secrets from history.
echo.
echo OPTION 1 - Manual Method (Recommended):
echo.
echo 1. Download BFG Repo Cleaner:
echo    https://rtyley.github.io/bfg-repo-cleaner/
echo.
echo 2. Run these commands:
echo    java -jar bfg.jar --delete-files secrets.toml
echo    java -jar bfg.jar --delete-files storage.env
echo    java -jar bfg.jar --delete-files storage.env.bak
echo    git reflog expire --expire=now --all
echo    git gc --prune=now --aggressive
echo    git push origin master --force
echo.
echo ============================================================
echo.
echo OPTION 2 - Git Filter-Repo (Better than filter-branch):
echo.
echo 1. Install git-filter-repo:
echo    pip install git-filter-repo
echo.
echo 2. Run:
echo    git filter-repo --path .streamlit/secrets.toml --invert-paths
echo    git filter-repo --path config/storage.env --invert-paths
echo    git filter-repo --path config/storage.env.bak --invert-paths
echo    git remote add origin https://github.com/bolajil/genai-knowledge-assistant.git
echo    git push origin master --force
echo.
echo ============================================================
echo.
echo OPTION 3 - Start Fresh (Easiest but loses history):
echo.
echo 1. Create new branch without secrets:
echo    git checkout --orphan clean-master
echo    git add .
echo    git commit -m "Clean start: Project cleanup without secrets"
echo    git branch -D master
echo    git branch -m master
echo    git push origin master --force
echo.
echo ============================================================
echo.
echo Which option would you like to use?
echo.
pause
