# Build and run the app. Windows.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Error "No .env found in $root. Create one with OPENROUTER_API_KEY and SESSION_SECRET."
}

docker build -t pm-app .
docker rm -f pm-app 2>$null | Out-Null
docker run -d `
    --name pm-app `
    -p 8000:8000 `
    --env-file .env `
    -v pm-data:/app/data `
    pm-app

Write-Output "Running at http://localhost:8000"
