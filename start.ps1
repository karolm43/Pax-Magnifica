# ============================================================
#  Custodian Engine - uruchom backend + frontend jednym poleceniem.
#  Uzycie:  w katalogu repo:  ./start.ps1   (lub kliknij start.cmd)
#
#  Startuje backend (FastAPI :8000) i frontend (Vite :5173) w osobnych oknach,
#  czeka az wstana i otwiera przegladarke na ekranie startowym.
#  Zamkniecie: zamknij oba okna PowerShella (lub Ctrl+C w kazdym).
# ============================================================

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Custodian Engine ==" -ForegroundColor Cyan

# 1) Zwolnij port 8000, gdyby trzymal go osierocony proces.
$held = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($held) {
    Write-Host "Zwalniam port 8000 (osierocony proces)..." -ForegroundColor Yellow
    $held.OwningProcess | Select-Object -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

# 2) Backend FastAPI w nowym oknie.
Write-Host "Startuje backend (FastAPI :8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location -LiteralPath '$root'; uv run python -m src.api"
)

# 3) Frontend: npm install przy pierwszym uruchomieniu, potem dev-serwer.
$frontend = Join-Path $root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Pierwsze uruchomienie - instaluje zaleznosci frontendu (npm install)..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "Startuje frontend (Vite :5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location -LiteralPath '$frontend'; npm run dev"
)

# 4) Poczekaj az frontend odpowie, potem otworz przegladarke.
Write-Host "Czekam na dev-serwer..." -ForegroundColor Cyan
$ok = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:5173/" -TimeoutSec 2 | Out-Null
        $ok = $true
        break
    } catch { }
}

if ($ok) {
    Start-Process "http://localhost:5173/"
    Write-Host "Gotowe. Przegladarka: http://localhost:5173/" -ForegroundColor Green
} else {
    Write-Host "Dev-serwer nie odpowiedzial w 30s - sprawdz okno frontendu." -ForegroundColor Red
    Write-Host "Recznie otworz: http://localhost:5173/"
}
