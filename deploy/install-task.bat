@echo off
REM ============================================================================
REM  AirFlow Lite - Instala a tarefa de auto-start no boot (Task Scheduler)
REM  EXECUTE COMO ADMINISTRADOR (clique-direito > Executar como administrador).
REM ============================================================================

set "TASK_NAME=AirFlowLite"
set "DEPLOY_DIR=%~dp0"
set "START_BAT=%DEPLOY_DIR%start.bat"

REM --- Verificar privilegio de administrador -----------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Este script precisa ser executado como ADMINISTRADOR.
    echo        Clique-direito ^> "Executar como administrador".
    pause
    exit /b 1
)

if not exist "%START_BAT%" (
    echo [ERRO] start.bat nao encontrado em %START_BAT%.
    exit /b 1
)

echo [..] Registrando tarefa "%TASK_NAME%" para iniciar no boot (conta SYSTEM)...
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "\"%START_BAT%\"" ^
    /SC ONSTART ^
    /RU SYSTEM ^
    /RL HIGHEST ^
    /F
if errorlevel 1 (
    echo [ERRO] Falha ao criar a tarefa.
    exit /b 1
)

echo.
echo [OK] Tarefa "%TASK_NAME%" criada. O servidor iniciara no proximo boot.
echo.
echo  Comandos uteis:
echo    Iniciar agora:   schtasks /Run    /TN "%TASK_NAME%"
echo    Ver status:      schtasks /Query  /TN "%TASK_NAME%"
echo    Parar:           schtasks /End    /TN "%TASK_NAME%"
echo    Remover:         deploy\uninstall-task.bat
echo.
echo  Obs.: para reinicio automatico em caso de falha, abra o Agendador de
echo        Tarefas, edite "%TASK_NAME%" ^> aba Configuracoes ^> "Reiniciar a cada".
echo.
pause
exit /b 0
