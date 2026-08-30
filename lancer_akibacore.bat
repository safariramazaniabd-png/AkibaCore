@echo off
REM ============================================================
REM  AkibaCore v2.2.0 - Script de lancement (Windows 10/11)
REM  Double-cliquer sur ce fichier pour lancer l'application.
REM ============================================================

cd /d "%~dp0"

echo.
echo   ==============================================
echo    AkibaCore v2.2.0 - Demarrage
echo   ==============================================
echo.

REM Priorite a l'executable autonome s'il est present
if exist "%~dp0AkibaCore.exe" (
    echo   Lancement de l'application...
    start "" "%~dp0AkibaCore.exe"
    exit /b 0
)

REM Sinon : lancement via Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERREUR : Python n'est pas installe ou pas dans le PATH.
    echo   Telechargez Python sur https://www.python.org/downloads/
    echo   et cochez "Add Python to PATH" pendant l'installation.
    pause
    exit /b 1
)

python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo   ERREUR : le module graphique tkinter est absent.
    echo   Reinstallez Python en cochant "tcl/tk and IDLE".
    pause
    exit /b 1
)

if not exist "%~dp0main.py" (
    echo   ERREUR : main.py introuvable dans %~dp0
    pause
    exit /b 1
)

echo   Lancement...
start "" pythonw "%~dp0main.py"
