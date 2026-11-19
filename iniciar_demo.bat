@echo off
REM Atalho da demonstracao (pode ir para a Area de Trabalho).
REM Acha sozinho a porta da Heltec RECEPTORA e abre a tela com os dados reais.
REM Se a receptora nao for encontrada, oferece o modo simulado (Plano B).
setlocal
cd /d "%~dp0" || (echo ERRO: nao consegui entrar na pasta & pause & exit /b 1)
title Cadeia de Frio - MNR 2026

set "PY=python"
where python >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"

echo Procurando a Heltec RECEPTORA no USB (ate uns 15 s)...
echo (Receptora no cabo de DADOS, transmissora e Uno ligados.)
set "PORTA="
for /f "delims=" %%P in ('"%PY%" tools\achar_portas.py --so-porta 2^>nul') do set "PORTA=%%P"

if defined PORTA (
  echo Receptora encontrada em %PORTA%. Abrindo a tela com o hardware real...
  call run_gateway.bat --port %PORTA% --demo-controls
  exit /b
)

echo.
echo Receptora NAO encontrada.
echo  - Confira: receptora no cabo de DADOS, antena, e nenhum outro programa usando a porta.
echo  - Para ver as portas: python tools\achar_portas.py
echo.
choice /c SN /m "Abrir o MODO SIMULADO (Plano B, declarar a banca)"
if errorlevel 2 exit /b 1
call run_gateway.bat --simulate --demo-controls
