# =============================================================================
# VeriUnlearn - one-command setup (Windows / PowerShell)
# Usage: .\scripts\setup.ps1 [-WithMonitoring] [-Seed] [-NoBuild]
# =============================================================================
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$WithMonitoring = $false
$Seed = $false
$NoBuild = $false
foreach ($arg in $args) {
    switch ($arg) {
        "--with-monitoring" { $WithMonitoring = $true }
        "--seed" { $Seed = $true }
        "--no-build" { $NoBuild = $true }
        "-h" { Get-Content $MyInvocation.MyCommand.Path | Where-Object { $_ -like "#*" }; exit 0 }
        default { Write-Error "Unknown argument: $arg"; exit 1 }
    }
}

function Test-Command($cmd) { Get-Command $cmd -ErrorAction SilentlyContinue }
if (-not (Test-Command docker)) { Write-Error "docker is required. Install from https://docs.docker.com/get-docker/"; exit 1 }

if (-not (Test-Path .env)) {
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "==> Created .env from .env.example"
    } else { Write-Error ".env.example not found"; exit 1 }
}

$profileArgs = @()
if ($WithMonitoring) { $profileArgs += "--profile"; $profileArgs += "monitoring" }

Write-Host "==> Starting VeriUnlearn stack..."
if ($NoBuild) { docker compose @profileArgs up -d }
else { docker compose @profileArgs up -d --build }

$port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$health = "http://localhost:$port/health"
Write-Host "==> Waiting for backend health..."
$ok = $false
for ($i = 1; $i -le 60; $i++) {
    try { $r = Invoke-WebRequest -Uri $health -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -eq 200) { $ok = $true; break } } catch {}
    Start-Sleep -Seconds 5
}
if (-not $ok) { Write-Error "Backend did not become healthy. Check: docker compose logs backend"; exit 1 }
Write-Host "==> Backend is healthy."

if ($Seed) {
    Write-Host "==> Seeding demo data..."
    if (Test-Path infra/scripts/seed_demo_data.py) {
        python infra/scripts/seed_demo_data.py --api-url "http://localhost:$port/api/v1"
    }
}

$fe = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
Write-Host ""
Write-Host "VeriUnlearn is up!"
Write-Host "  Frontend : http://localhost:$fe"
Write-Host "  API docs : http://localhost:$port/docs"
Write-Host "  Tear down: .\scripts\teardown.ps1"
