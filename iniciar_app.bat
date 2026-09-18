@echo off
title AutoCut Studio - Editor Automatico de Video Local
chcp 65001 > nul

echo ========================================================
echo   AutoCut Studio - Edición Automática de Video para YouTube
echo ========================================================
echo.
echo [1/2] Abriendo interfaz web en tu navegador...
start "" "frontend\index.html"

echo [2/2] Iniciando servidor backend local en http://127.0.0.1:8000 ...
echo.
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo ========================================================
echo.

backend\venv\Scripts\python.exe backend\main.py

pause
