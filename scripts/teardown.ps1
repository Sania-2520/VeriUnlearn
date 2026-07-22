# =============================================================================
# VeriUnlearn - one-command teardown (Windows / PowerShell)
# Usage: .\scripts\teardown.ps1 [-Volumes] [-All]
# =============================================================================
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Volumes = $false
$All = $false
foreach ($arg in $args) {
    switch ($arg) {
        "--volumes" { $Volumes = $true }
        "--all" { $Volumes = $true; $All = $true }
        default { Write-Error "Unknown argument: $arg"; exit 1 }
    }
}

Write-Host "==> Stopping VeriUnlearn stack..."
docker compose down
if ($Volumes) { docker compose down --volumes }
docker compose --profile monitoring down @(if ($Volumes) { "--volumes" })

if ($All) {
    Write-Host "==> Removing images..."
    docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "veriunlearn" } | ForEach-Object { docker rmi -f $_ }
}
Write-Host "Teardown complete."
