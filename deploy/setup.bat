@echo off
setlocal EnableDelayedExpansion
REM ============================================================================
REM  AirFlow Lite - Setup (instalacao)
REM  Cria a venv, instala dependencias, gera o .env.bat e o usuario admin.
REM  Execute a partir de qualquer lugar: deploy\setup.bat
REM ============================================================================

set "DEPLOY_DIR=%~dp0"
pushd "%DEPLOY_DIR%.." || (echo [ERRO] Nao foi possivel acessar a pasta do projeto. & exit /b 1)
set "PROJECT_DIR=%CD%"

echo ============================================================
echo   AirFlow Lite - Setup
echo   Projeto: %PROJECT_DIR%
echo ============================================================
echo.

REM --- 1. Verificar Python -----------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo        Instale o Python 3.8+ e marque "Add Python to PATH".
    popd & exit /b 1
)
echo [OK] Python encontrado:
python --version
echo.

REM --- 2. Criar a venv ---------------------------------------------------------
if exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    echo [OK] venv ja existe, pulando criacao.
) else (
    echo [..] Criando ambiente virtual em venv\ ...
    python -m venv "%PROJECT_DIR%\venv"
    if errorlevel 1 (echo [ERRO] Falha ao criar a venv. & popd & exit /b 1)
    echo [OK] venv criada.
)
echo.

REM --- 3. Instalar dependencias ------------------------------------------------
echo [..] Instalando dependencias (requirements.txt) ...
call "%PROJECT_DIR%\venv\Scripts\activate.bat"

REM Compatibilidade com venv baseada em Anaconda/Miniconda (DLLs como _sqlite3).
set "PY_HOME="
for /f "tokens=1,* delims== " %%a in ('type "%PROJECT_DIR%\venv\pyvenv.cfg"') do (
    if /i "%%a"=="home" set "PY_HOME=%%b"
)
REM Nao adicionar a raiz do PY_HOME (tem python.exe e sombrearia a venv).
if defined PY_HOME if exist "%PY_HOME%\Library\bin" set "PATH=%PY_HOME%\Library\bin;%PY_HOME%\DLLs;%PATH%"

python -m pip install --upgrade pip
pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 (echo [ERRO] Falha ao instalar dependencias. & popd & exit /b 1)
echo [OK] Dependencias instaladas.
echo.

REM --- 4. Criar .env.bat (com SECRET_KEY gerada) -------------------------------
set "ENV_FILE=%DEPLOY_DIR%.env.bat"
set "ENV_EXAMPLE=%DEPLOY_DIR%.env.bat.example"
if exist "%ENV_FILE%" (
    echo [OK] %ENV_FILE% ja existe, mantendo configuracao atual.
) else (
    echo [..] Gerando SECRET_KEY e criando .env.bat ...
    for /f "delims=" %%k in ('python -c "import secrets;print(secrets.token_hex(32))"') do set "NEWKEY=%%k"
    python -c "import sys;p=r'%ENV_EXAMPLE%';o=r'%ENV_FILE%';s=open(p,encoding='utf-8').read();s=s.replace('MUDE-ESTA-CHAVE-EM-PRODUCAO','%NEWKEY%');open(o,'w',encoding='utf-8').write(s)"
    if errorlevel 1 (echo [ERRO] Falha ao criar .env.bat. & popd & exit /b 1)
    echo [OK] %ENV_FILE% criado com SECRET_KEY aleatoria.
    echo      ^>^> EDITE-O e ajuste ALLOWED_SCRIPT_DIRS e DATABASE_URL antes de iniciar.
)
echo.

REM --- 5. Criar usuario admin --------------------------------------------------
echo [..] Carregando variaveis de ambiente ...
call "%ENV_FILE%"
set "FLASK_APP=run.py"
echo.
echo [..] Criando usuario administrador (interativo) ...
flask create-admin
echo.

echo ============================================================
echo   Setup concluido.
echo   Proximos passos:
echo     1) Edite deploy\.env.bat (ALLOWED_SCRIPT_DIRS, DATABASE_URL)
echo     2) Teste:        deploy\start.bat
echo     3) Auto-start:   clique-direito deploy\install-task.bat
echo                      ^> "Executar como administrador"
echo ============================================================
popd
endlocal
exit /b 0
