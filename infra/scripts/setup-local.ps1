#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script setup environment lokal untuk AI Chatbot MVP.
    Jalankan dari root folder: .\infra\scripts\setup-local.ps1
.NOTES
    Prasyarat: Python 3.12, Node.js 22, Docker Desktop, Git
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== AI Chatbot MVP — Setup Lokal ===" -ForegroundColor Cyan

# ── Cek tools ──────────────────────────────────────────────────────────
function Check-Tool {
    param($Name, $Command, $HelpUrl)
    try {
        $null = & $Command --version 2>&1
        Write-Host "  ✓ $Name ditemukan" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $Name TIDAK ditemukan. Install dari: $HelpUrl" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nMemeriksa tools yang diperlukan..." -ForegroundColor Yellow
Check-Tool "Python 3.12" "python" "https://python.org"
Check-Tool "Node.js 22" "node" "https://nodejs.org"
Check-Tool "npm" "npm" "https://nodejs.org"
Check-Tool "Docker" "docker" "https://docker.com/products/docker-desktop"
Check-Tool "Git" "git" "https://git-scm.com"

# ── Env file ───────────────────────────────────────────────────────────
Write-Host "`nMenyiapkan .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  .env dibuat dari .env.example" -ForegroundColor Green
    Write-Host "  ⚠ PENTING: Edit .env dan isi nilai yang sesuai sebelum lanjut!" -ForegroundColor Yellow
} else {
    Write-Host "  .env sudah ada" -ForegroundColor Green
}

# ── Backend venv ────────────────────────────────────────────────────────
Write-Host "`nMenyiapkan Python virtual environment backend..." -ForegroundColor Yellow
Set-Location "services\api"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  .venv dibuat" -ForegroundColor Green
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
& ".venv\Scripts\pip.exe" install -r requirements.txt -q
Write-Host "  Dependency backend terinstall" -ForegroundColor Green
Set-Location "..\..\"

# ── Frontend npm ────────────────────────────────────────────────────────
Write-Host "`nMenginstall dependency frontend..." -ForegroundColor Yellow
Set-Location "apps\web"
if (Test-Path "package-lock.json") {
    npm ci --prefer-offline --silent
} else {
    npm install --silent
    Write-Host "  Membuat package-lock.json baru" -ForegroundColor Yellow
}
Write-Host "  Dependency frontend terinstall" -ForegroundColor Green
Set-Location "..\..\"

# ── Docker Compose check ────────────────────────────────────────────────
Write-Host "`nMemvalidasi Docker Compose..." -ForegroundColor Yellow
docker compose config --quiet
Write-Host "  compose.yaml valid" -ForegroundColor Green

# ── Selesai ─────────────────────────────────────────────────────────────
Write-Host @"

=== Setup selesai! ===

Langkah selanjutnya:
  1. Edit .env dan isi POSTGRES_PASSWORD, APP_SECRET_KEY, JWT_SECRET_KEY
  2. Jalankan: docker compose up -d postgres
  3. Tunggu healthy, lalu: docker compose up -d api web nginx
  4. Buka: http://localhost

Perintah berguna:
  docker compose ps             → cek status
  docker compose logs -f api    → lihat log backend
  docker compose exec api alembic upgrade head  → jalankan migrasi

"@ -ForegroundColor Cyan
