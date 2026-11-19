# Prepara o prototipo (Uno + 2 Heltec) para rodar com o gateway, de ponta a ponta.
# Uso (PowerShell, na pasta do projeto):
#   powershell -ExecutionPolicy Bypass -File tools\preparar_prototipo.ps1
# Para nas trocas de placa e espera ENTER. Guia: docs/PROTOTIPO_UNO.md
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = "python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
}

function Passo($t) { Write-Host ""; Write-Host "==== $t ====" -ForegroundColor Cyan }
function Falha($t) { Write-Host ""; Write-Host "ERRO: $t" -ForegroundColor Red; Read-Host "ENTER para sair"; exit 1 }
function Roda { & $py @args; if ($LASTEXITCODE -ne 0) { Falha "comando falhou: $args" } }

# Porta da Heltec (chip CP210x, VID 10C4). Se houver mais de uma, pergunta.
function Porta-Heltec {
    $ports = & $py -c "import serial.tools.list_ports as l; print('\n'.join(p.device for p in l.comports() if p.vid == 0x10C4))"
    $ports = @($ports | Where-Object { $_ })
    if ($ports.Count -eq 1) { return $ports[0] }
    if ($ports.Count -eq 0) { Falha "nenhuma Heltec no USB. Confira o cabo de dados e o driver CP210x." }
    Write-Host "Mais de uma Heltec ligada: $($ports -join ', ')" -ForegroundColor Yellow
    return (Read-Host "Digite a porta da placa certa (ex.: COM3)")
}

Passo "1/7 Atualizando o projeto"
git pull
if ($LASTEXITCODE -ne 0) { Falha "git pull falhou (conflito?). Mande o print." }

Passo "2/7 Chave do no 1"
if (Test-Path "firmware\include\keys.h") {
    Write-Host "Chave ja existe, mantendo (keys.h e keys\nodes.json)."
} else {
    Roda tools\provision_node.py --node-id 1
}

Passo "3/7 Compilando os dois firmwares (pode levar alguns minutos)"
Roda -m platformio run -d firmware\node -e heltec_v3_node_uno
Roda -m platformio run -d firmware\receiver

Passo "4/7 Gravando a TRANSMISSORA"
Write-Host "1. Antena rosqueada na transmissora."
Write-Host "2. Ligue no USB SOMENTE a transmissora (a que tem os fios do divisor)."
Write-Host "3. Deixe o Arduino Uno ligado (USB ou powerbank)."
Read-Host "ENTER quando estiver pronto"
$tx = Porta-Heltec
Write-Host "Transmissora em $tx"
Roda -m platformio run -d firmware\node -e heltec_v3_node_uno -t upload --upload-port $tx
Write-Host "Conferindo as assinaturas por 30 s (espere linhas INFO,uno e ACEITO)..."
Start-Sleep -Seconds 3
& $py tools\check_fw_output.py --port $tx --seconds 30
if ($LASTEXITCODE -ne 0) {
    Write-Host "A conferencia nao passou. Sem 'INFO,uno': confira fio amarelo (ponto X), roxo (GND) e o Uno ligado." -ForegroundColor Yellow
    if ((Read-Host "Continuar mesmo assim? (s/n)") -ne "s") { exit 1 }
}

Passo "5/7 Trocando de placa"
Write-Host "1. Tire a transmissora do notebook e ligue no POWERBANK."
Write-Host "2. Antena rosqueada na receptora."
Write-Host "3. Ligue no USB SOMENTE a receptora."
Read-Host "ENTER quando estiver pronto"
$rx = Porta-Heltec
Write-Host "Receptora em $rx"

Passo "6/7 Gravando a RECEPTORA"
Roda -m platformio run -d firmware\receiver -t upload --upload-port $rx
Write-Host "Conferindo a recepcao por 30 s (espere linhas RX e ACEITO)..."
Start-Sleep -Seconds 3
& $py tools\check_fw_output.py --port $rx --seconds 30
if ($LASTEXITCODE -ne 0) {
    Write-Host "Nada aceito. Confira as duas antenas e se a transmissora esta no powerbank." -ForegroundColor Yellow
    if ((Read-Host "Abrir a tela mesmo assim? (s/n)") -ne "s") { exit 1 }
}

Passo "7/7 Abrindo a tela com dados reais ($rx)"
Write-Host "Na tela: clique em Restaurar demo e faca os testes. Para parar: Ctrl+C."
& .\run_gateway.bat --port $rx --demo-controls
