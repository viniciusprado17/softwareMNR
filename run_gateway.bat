@echo off
REM Tela do gateway no Windows. Duplo clique = modo simulado (sem hardware).
REM Com o receptor no USB:  run_gateway.bat --port COM5 --demo-controls
setlocal
cd /d "%~dp0" || (echo ERRO: nao consegui entrar na pasta "%~dp0" & pause & exit /b 1)

REM Ambiente incompleto de uma tentativa anterior: recria do zero.
if exist .venv\ if not exist .venv\Scripts\python.exe rmdir /s /q .venv

if not exist .venv\Scripts\python.exe (
  echo [1/2] Criando ambiente Python em .venv ...
  python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo Tentando com o lancador py ...
    py -3 -m venv .venv
  )
  if not exist .venv\Scripts\python.exe (
    echo.
    echo ERRO: nao foi possivel criar o ambiente. Confira no cmd:  python --version
    echo Precisa ser 3.10 ou maior, instalado com "Add python.exe to PATH".
    pause
    exit /b 1
  )
  echo [2/2] Instalando dependencias, leva 1 a 2 minutos ...
  .venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo.
    echo ERRO na instalacao. Confira a internet e rode de novo. Se persistir, mande print desta janela.
    rmdir /s /q .venv
    pause
    exit /b 1
  )
)

set "PYTHONPATH=%CD%\src"
echo.
echo Abrindo http://127.0.0.1:8000 em alguns segundos. Deixe esta janela ABERTA (fechar = desligar).
start "" cmd /c "timeout /t 5 >/dev/null & start http://127.0.0.1:8000"
if "%~1"=="" (
  .venv\Scripts\python.exe -m coldchain.webapp --simulate --demo-controls
) else (
  .venv\Scripts\python.exe -m coldchain.webapp %*
)
echo.
echo O gateway parou.
pause
