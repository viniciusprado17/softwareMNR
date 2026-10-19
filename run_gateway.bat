@echo off
REM Tela do gateway no Windows. Duplo clique = modo simulado (sem hardware).
REM Com o receptor no USB:  run_gateway.bat --port COM5 --demo-controls
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Primeira execucao: criando ambiente e instalando dependencias...
  py -3 -m venv .venv 2>/dev/null || python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo ERRO: Python 3.10+ nao encontrado. Instale em https://www.python.org/downloads/
    echo e marque "Add python.exe to PATH" durante a instalacao.
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install -r requirements.txt
)
set PYTHONPATH=%~dp0src
start "" cmd /c "timeout /t 4 >/dev/null & start http://127.0.0.1:8000"
if "%~1"=="" (
  .venv\Scripts\python -m coldchain.webapp --simulate --demo-controls
) else (
  .venv\Scripts\python -m coldchain.webapp %*
)
pause
