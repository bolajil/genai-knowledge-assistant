param([switch]$Execute, [switch]$DryRun)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path ".").Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $Root ("archive_conflict_backups/" + $timestamp)

# Collect candidate files
$files = Get-ChildItem -Path $Root -Recurse -File -Include *.py,*.md,*.txt,*.yml,*.yaml -ErrorAction SilentlyContinue

$pattern = '(?ms)<<<<<<< HEAD\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>>[^\r\n]*\r?\n?'
$changed = 0

foreach ($f in $files) {
  try {
    $content = Get-Content -Path $f.FullName -Raw -ErrorAction Stop
  } catch {
    continue
  }
  if ($content -notmatch '<<<<<<<') { continue }

  $new = $content
  $iterations = 0
  while ($new -match '<<<<<<<' -and $iterations -lt 200) {
    $prev = $new
    $new = [regex]::Replace($new, $pattern, '$1')
    if ($new -eq $prev) { break }
    $iterations++
  }

  if ($new -ne $content) {
    $changed++
    if ($DryRun) {
      Write-Host "Would fix: $($f.FullName)"
    } elseif ($Execute) {
      $rel = $f.FullName.Substring($Root.Length).TrimStart('\\','/')
      $backupFile = Join-Path $backupDir $rel
      New-Item -ItemType Directory -Force -Path (Split-Path $backupFile) | Out-Null
      Copy-Item -Force $f.FullName $backupFile
      Set-Content -Path $f.FullName -Value $new -Encoding UTF8
      Write-Host "Fixed: $($f.FullName)"
    }
  }
}

Write-Host "Files with conflicts modified: $changed"
if ($DryRun) { Write-Host "Dry-run complete. Re-run with -Execute to apply fixes. Backups will be stored under: $backupDir" }
