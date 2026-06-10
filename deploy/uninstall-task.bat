@echo off
REM ============================================================================
REM  AirFlow Lite - Remove a tarefa de auto-start (Task Scheduler)
REM  EXECUTE COMO ADMINISTRADOR.
REM ============================================================================

set "TASK_NAME=AirFlowLite"

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Este script precisa ser executado como ADMINISTRADOR.
    pause
    exit /b 1
)

echo [..] Parando e removendo a tarefa "%TASK_NAME%" ...
schtasks /End /TN "%TASK_NAME%" >nul 2>&1
schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
    echo [ERRO] Falha ao remover a tarefa (talvez ja nao exista).
    exit /b 1
)
echo [OK] Tarefa "%TASK_NAME%" removida.
pause
exit /b 0
