# Prepara um notebook Windows para o projeto MNR 2026 (etapa E0).
# Uso (PowerShell): powershell -ExecutionPolicy Bypass -File setup_notebook.ps1
$ErrorActionPreference = "Stop"
$base = Join-Path $env:USERPROFILE "Projetos"
$repo = Join-Path $base "softwareMNR"
$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

Write-Host "1/6 Git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements --silent
    $env:Path += ";C:\Program Files\Git\cmd"
}

Write-Host "2/6 Python 3.12"
if (-not (Test-Path $py)) {
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements --silent
}
& $py --version

Write-Host "3/6 Repositorio (ramo main)"
New-Item -ItemType Directory -Force $base | Out-Null
if (-not (Test-Path $repo)) {
    git clone -b main https://github.com/viniciusprado17/softwareMNR.git $repo
} else {
    git -C $repo checkout main; git -C $repo pull
}

Write-Host "4/6 Dependencias (inclui PlatformIO)"
& $py -m pip install --upgrade pip -q
& $py -m pip install -r (Join-Path $repo "requirements-dev.txt") -q --no-warn-script-location
& $py -m platformio --version

Write-Host "5/6 Testes"
Push-Location $repo
& $py -m unittest discover -s tests
Pop-Location

Write-Host "6/6 Compilando o vectest (a primeira vez leva uns 5 minutos)"
Push-Location (Join-Path $repo "firmware\vectest")
& $py -m platformio run
Pop-Location

Write-Host "PRONTO. Projeto em $repo"
