@echo off
REM Teste completo com o hardware (abra antes o iniciar_demo.bat e deixe a tela aberta).
setlocal
cd /d "%~dp0"
title Teste ponta a ponta - MNR 2026
set "PY=python"
where python >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%PY%" tools\teste_ponta_a_ponta.py --adulteracoes 50 --pacotes 3
echo.
pause
