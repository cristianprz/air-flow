@echo off
REM ============================================================================
REM  AirFlow Lite - Start (servidor de producao via Waitress)
REM  Carrega o .env.bat, ativa a venv e inicia serve.py.
REM  E este o comando disparado pelo Task Scheduler no boot.
REM ============================================================================

set "DEPLOY_DIR=%~dp0"
pushd "%DEPLOY_DIR%.." || exit /b 1
set "PROJECT_DIR=%CD%"

REM --- Carregar variaveis de ambiente -----------------------------------------
if not exist "%DEPLOY_DIR%.env.bat" (
    echo [ERRO] %DEPLOY_DIR%.env.bat nao encontrado. Rode deploy\setup.bat primeiro.
    popd & exit /b 1
)
call "%DEPLOY_DIR%.env.bat"

REM --- Ativar a venv ----------------------------------------------------------
if not exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    echo [ERRO] venv nao encontrada. Rode deploy\setup.bat primeiro.
    popd & exit /b 1
)
call "%PROJECT_DIR%\venv\Scripts\activate.bat"

REM --- Compatibilidade com venv baseada em Anaconda/Miniconda ------------------
REM Se a venv foi criada a partir do Python do (Ana/Mini)conda, ela depende das
REM DLLs do interpretador base (ex.: _sqlite3 precisa de Library\bin). Fora de um
REM shell conda ativo (ex.: conta SYSTEM no boot) isso falha. Lemos o caminho base
REM do pyvenv.cfg e o adicionamos ao PATH, sem hardcode.
set "PY_HOME="
for /f "tokens=1,* delims== " %%a in ('type "%PROJECT_DIR%\venv\pyvenv.cfg"') do (
    if /i "%%a"=="home" set "PY_HOME=%%b"
)
REM IMPORTANTE: NAO adicionar a raiz do PY_HOME ao PATH (ela tem python.exe e
REM sombrearia o python da venv). Apenas Library\bin e DLLs, que contem as DLLs
REM nativas (ex.: sqlite3.dll) sem nenhum python.exe.
if defined PY_HOME (
    if exist "%PY_HOME%\Library\bin" set "PATH=%PY_HOME%\Library\bin;%PY_HOME%\DLLs;%PATH%"
)

REM --- Iniciar o servidor -----------------------------------------------------
REM Saida (incluindo tracebacks) vai para um log, pois ao rodar como SYSTEM no
REM boot nao ha console visivel. Veja PROJECT_DIR\server.log para diagnosticar.
set "LOG_FILE=%PROJECT_DIR%\server.log"
echo. >> "%LOG_FILE%"
echo [%date% %time%] Iniciando AirFlow Lite em %HOST%:%PORT% ... >> "%LOG_FILE%"
python "%PROJECT_DIR%\serve.py" >> "%LOG_FILE%" 2>&1
set "RC=%errorlevel%"
echo [%date% %time%] Servidor encerrado (codigo %RC%). >> "%LOG_FILE%"

popd
exit /b %RC%
