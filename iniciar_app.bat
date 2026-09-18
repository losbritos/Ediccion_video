@echo off
title AutoCut Studio - Editor Automatico de Video Local

echo ========================================================
echo   AutoCut Studio - Edicion Automatica de Video
echo ========================================================
echo.
echo [1/2] Abriendo AutoCut Studio en tu navegador: http://127.0.0.1:8000
start http://127.0.0.1:8000

echo [2/2] Iniciando servidor backend local...
echo Presiona Ctrl+C para detener el servidor.
echo ========================================================
echo.

backend\venv\Scripts\python.exe backend\main.py

pause
