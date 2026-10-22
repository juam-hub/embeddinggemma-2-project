@echo off
cd /d "%~dp0"
chcp 65001 > nul
setlocal enabledelayedexpansion

echo =====================================================================
echo       CRIATURA LÍQUIDA: RAG MULTIMODAL (QWEN2.5-VL + GEMMA-2)
echo =====================================================================
echo.

REM 1. Verificar existencia del entorno virtual .venv
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontró el entorno virtual local .venv en este directorio.
    echo Creando entorno virtual e instalando dependencias...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR CRITICO] Falló la creación de .venv con python.
        echo Asegúrate de tener Python 3.10+ instalado y agregado al PATH.
        pause
        exit /b 1
    )
    .\.venv\Scripts\pip.exe install -r requirements.txt
)

REM 2. Verificar estado de Qdrant en http://127.0.0.1:6333
echo [1/3] Verificando base vectorial Qdrant en http://127.0.0.1:6333 ...
curl.exe -s http://127.0.0.1:6333/ > nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Qdrant ya se encuentra activo en el puerto 6333.
    goto CHECK_OLLAMA
)

echo Iniciando contenedor de Qdrant con Docker Compose...
docker compose up -d > nul 2>&1
if !errorlevel! neq 0 (
    echo [ADVERTENCIA] No se pudo ejecutar 'docker compose up -d'.
    echo Verificando si Docker Desktop está abierto...
)

REM Esperar hasta 10 segundos a que Qdrant responda
set RETRIES=0
:WAIT_QDRANT
curl.exe -s http://127.0.0.1:6333/ > nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Qdrant iniciado y listo.
    goto CHECK_OLLAMA
)
set /a RETRIES+=1
if !RETRIES! geq 10 (
    echo [ADVERTENCIA] Qdrant no respondió en http://127.0.0.1:6333/.
    echo Si vas a utilizar búsqueda vectorial, por favor asegúrate de que Docker Desktop esté corriendo.
    goto CHECK_OLLAMA
)
timeout /t 1 > nul
goto WAIT_QDRANT

:CHECK_OLLAMA
REM 3. Verificar estado de Ollama local (opcional para modo nube)
echo.
echo [2/3] Verificando servidor Ollama local en http://127.0.0.1:11434 ...
curl.exe -s http://127.0.0.1:11434/ > nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Ollama está activo y listo para inferencia local.
) else (
    echo [INFO] Ollama no está activo en segundo plano.
    echo        Nota: Solo es necesario si seleccionas el modelo Local Qwen2.5-VL.
    echo        Para modelos en la nube mediante API no es requerido.
)

:LAUNCH
REM 4. Liberar puerto 8501 si quedó una instancia previa de Streamlit
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":8501.*LISTENING"') do (
    echo [INFO] Liberando puerto 8501 de una sesion anterior [PID %%a]...
    taskkill /F /PID %%a > nul 2>&1
)

REM 5. Lanzar la aplicación Streamlit usando el python local de .venv
echo.
echo [3/3] Iniciando la Criatura Líquida...
echo.
echo =====================================================================
echo  Abriendo Criatura Líquida en tu navegador predeterminado...
echo  URL Local: http://localhost:8501
echo  Para detener el servidor presiona CTRL + C en esta ventana
echo =====================================================================
echo.

.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.headless false

if !errorlevel! neq 0 (
    echo.
    echo [AVISO] La aplicación se ha detenido con código de salida: !errorlevel!
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul
