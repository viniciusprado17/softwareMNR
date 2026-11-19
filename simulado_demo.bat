@echo off
REM Plano B: tela no modo simulado (sem placas). Declarar a banca que e simulacao.
cd /d "%~dp0"
call run_gateway.bat --simulate --demo-controls
