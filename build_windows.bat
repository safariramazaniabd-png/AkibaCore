@echo off
REM ============================================================
REM  Script de compilation AVEC Bukavu -> AVEC_Bukavu.exe
REM  A executer UNE SEULE FOIS sur ta machine Windows
REM ============================================================

echo === Verification de Python ===
python --version
if errorlevel 1 (
    echo ERREUR : Python n'est pas installe ou pas dans le PATH.
    echo Telecharge Python 3.10+ sur https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo === Installation de PyInstaller ===
pip install pyinstaller --upgrade
if errorlevel 1 (
    echo ERREUR lors de l'installation de PyInstaller.
    pause
    exit /b 1
)

echo.
echo === Compilation de l'executable ===
pyinstaller avec_bukavu.spec --clean
if errorlevel 1 (
    echo ERREUR lors de la compilation.
    pause
    exit /b 1
)

echo.
echo === Nettoyage des fichiers temporaires ===
rmdir /s /q build 2>nul
rmdir /s /q __pycache__ 2>nul

echo.
echo ============================================================
echo  SUCCES !
echo  Votre executable se trouve dans :
echo    dist\AVEC_Bukavu.exe
echo.
echo  Pour distribuer le logiciel, copiez UNIQUEMENT ce fichier.
echo  La base de donnees avec_bukavu.db sera creee automatiquement
echo  dans le meme dossier que l'executable au premier lancement.
echo ============================================================
pause
