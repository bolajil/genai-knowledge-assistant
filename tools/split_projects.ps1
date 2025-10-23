param(
  [string]$DemoOut = "dist/vaultmind-demo",
  [string]$DashboardOut = "dist/vaultmind-dashboard",
  [switch]$Execute,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null }
}

function Copy-Safe([string]$src, [string]$dst) {
  if (Test-Path $src) {
    if ($DryRun) { Write-Host "DRYRUN copy $src -> $dst"; return }
    Ensure-Dir (Split-Path $dst)
    Copy-Item -Recurse -Force $src $dst
  } else {
    Write-Host "Skip (not found): $src"
  }
}

function Write-File([string]$path, [string]$content) {
  if ($DryRun) { Write-Host "DRYRUN write $path"; return }
  Ensure-Dir (Split-Path $path)
  Set-Content -Path $path -Value $content -Encoding UTF8
}

# Create root dist folders
Ensure-Dir "dist"
Ensure-Dir $DemoOut
Ensure-Dir $DashboardOut

# --------------- DEMO APP BUILD -----------------
# Copy the publish demo app content
Copy-Safe "publish/VaultMind-Demo/*" (Join-Path $DemoOut ".")
# Minimal utils required by demo app
Copy-Safe "utils/vector_search_with_embeddings.py" (Join-Path $DemoOut "utils/vector_search_with_embeddings.py")
Copy-Safe "utils/demo_mode.py" (Join-Path $DemoOut "utils/demo_mode.py")
# Shared config and data
Copy-Safe "config" (Join-Path $DemoOut "config")
Copy-Safe "data" (Join-Path $DemoOut "data")

# Generate minimal requirements for Demo
$demoReq = @"
streamlit>=1.36
python-dotenv>=1.0
requests>=2.31
pandas>=2.0
sentence-transformers>=2.2
faiss-cpu>=1.7
numpy>=1.24
"@
Write-File (Join-Path $DemoOut "requirements.txt") $demoReq

# --------------- DASHBOARD APP BUILD -----------------
# Entry + tabs + app + utils + config + data
Copy-Safe "genai_dashboard_modular.py" (Join-Path $DashboardOut "genai_dashboard_modular.py")
Copy-Safe "tabs" (Join-Path $DashboardOut "tabs")
Copy-Safe "app" (Join-Path $DashboardOut "app")
Copy-Safe "utils" (Join-Path $DashboardOut "utils")
Copy-Safe "config" (Join-Path $DashboardOut "config")
Copy-Safe "data" (Join-Path $DashboardOut "data")

# Requirements for Dashboard (broader)
$dashReq = @"
streamlit>=1.36
python-dotenv>=1.0
requests>=2.31
pandas>=2.0
numpy>=1.24
faiss-cpu>=1.7
sentence-transformers>=2.2
pydantic>=2.6
scikit-learn>=1.3
redis>=5.0
transformers>=4.42
weaviate-client>=4.6
openai>=1.30
"@
Write-File (Join-Path $DashboardOut "requirements.txt") $dashReq

# Root READMEs
$demoReadme = @"
# VaultMIND Demo App

Run a minimal search + LLM synthesis demo.

## Quickstart

```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
streamlit run publish/VaultMind-Demo/enhanced_streamlit_app.py
```

Place your FAISS indexes under `data/indexes/`.
"@
Write-File (Join-Path $DemoOut "README.md") $demoReadme

$dashReadme = @"
# VaultMIND Dashboard

Full multi-tab dashboard with authentication and enterprise features.

## Quickstart
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
streamlit run genai_dashboard_modular.py
```

Indexes in `data/`, configuration in `config/`.
"@
Write-File (Join-Path $DashboardOut "README.md") $dashReadme

Write-Host "Split prepared:"
Write-Host " - Demo:      $DemoOut"
Write-Host " - Dashboard: $DashboardOut"

if ($Execute) { Write-Host "Split complete." } else { Write-Host "Dry-run complete. No files moved without -Execute." }
