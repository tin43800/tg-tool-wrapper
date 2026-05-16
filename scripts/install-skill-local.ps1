# Symlink the telegram-deployer skill into ~/.claude/skills/ for local development.
# Run from PowerShell as Administrator (symlinks need admin on Windows).

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SkillSrc = Join-Path $RepoRoot "skills/telegram-deployer"
$SkillDst = Join-Path $env:USERPROFILE ".claude/skills/telegram-deployer"

if (-not (Test-Path $SkillSrc)) {
    Write-Error "Source skill not found: $SkillSrc"
    exit 1
}

$SkillsDir = Join-Path $env:USERPROFILE ".claude/skills"
if (-not (Test-Path $SkillsDir)) {
    New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null
}

if (Test-Path $SkillDst) {
    Write-Warning "$SkillDst already exists — removing"
    Remove-Item $SkillDst -Recurse -Force
}

New-Item -ItemType SymbolicLink -Path $SkillDst -Target $SkillSrc | Out-Null
Write-Host "✅ Linked $SkillDst → $SkillSrc" -ForegroundColor Green
Write-Host "Restart Claude Code (or start a new session) and the 'telegram-deployer' skill will be available."
