param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if ($Clean) {
    if (Test-Path "$projectRoot\build") {
        Remove-Item -Recurse -Force "$projectRoot\build"
    }
    if (Test-Path "$projectRoot\dist") {
        Remove-Item -Recurse -Force "$projectRoot\dist"
    }
}

python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm Intel.spec

$distRoot = Join-Path $projectRoot "dist\Intel"

New-Item -ItemType Directory -Force -Path (Join-Path $distRoot "data\input") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $distRoot "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $distRoot "data\sounds") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $distRoot "data\wakeword\models") | Out-Null

Copy-Item "$projectRoot\data\sounds\*" (Join-Path $distRoot "data\sounds") -Force
Copy-Item "$projectRoot\data\wakeword\models\*" (Join-Path $distRoot "data\wakeword\models") -Force

if (-not (Test-Path (Join-Path $distRoot ".env"))) {
    Copy-Item "$projectRoot\.env.example" (Join-Path $distRoot ".env")
}

Write-Host ""
Write-Host "Portable build is ready:" -ForegroundColor Green
Write-Host "  $distRoot"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit $distRoot\.env"
Write-Host "  2. Make sure Ollama + gemma3 are installed on the target machine"
Write-Host "  3. Run $distRoot\Intel.exe"
