# Cria a pasta "MNR 2026" na Area de Trabalho com os atalhos da demonstracao.
# Uso: powershell -ExecutionPolicy Bypass -File tools\criar_atalhos.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$desk = [Environment]::GetFolderPath("Desktop")
$pasta = Join-Path $desk "MNR 2026"
New-Item -ItemType Directory -Force $pasta | Out-Null
$sh = New-Object -ComObject WScript.Shell

function Atalho($nome, $alvo, $descricao) {
    $lnk = $sh.CreateShortcut((Join-Path $pasta "$nome.lnk"))
    $lnk.TargetPath = $alvo
    $lnk.WorkingDirectory = $repo
    $lnk.Description = $descricao
    $lnk.Save()
    Write-Host "  criado: $nome"
}

Write-Host "Criando atalhos em $pasta"
Atalho "1 - Iniciar demonstracao" (Join-Path $repo "iniciar_demo.bat") "Acha a receptora e abre a tela com o hardware real"
Atalho "2 - Teste completo" (Join-Path $repo "testar_demo.bat") "Confere pacotes, adulteracao, replay e corrente (tela aberta antes)"
Atalho "3 - Plano B modo simulado" (Join-Path $repo "simulado_demo.bat") "Tela sem placas; declarar que e simulacao"
Atalho "Roteiro da demonstracao" (Join-Path $repo "docs\ROTEIRO_DEMO.md") "Roteiro de 5 minutos, limites e checklist"
Atalho "Medicoes" (Join-Path $repo "docs\MEDICOES.md") "Tudo o que foi medido, com data"
Atalho "Manual do prototipo" (Join-Path $repo "prototipo_lacor\Guia_da_equipe_LACOR_MNR.pdf") "Ligacoes e montagem (18/11)"
Atalho "Pasta do projeto" $repo "softwareMNR"
Write-Host "Pronto. Abra a pasta MNR 2026 na Area de Trabalho."
explorer.exe $pasta
