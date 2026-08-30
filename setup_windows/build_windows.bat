@echo off
REM ============================================================
REM  Script de compilation AkibaCore v2.2.0 -> AkibaCore.exe
REM  A executer sur une machine Windows 10/11
REM  Prerequis : Python 3.8+ installe (cocher "Add to PATH")
REM ============================================================

REM On travaille depuis la racine du projet (parents de setup_windows\)
pushd "%~dp0.."

echo === Verification de Python ===
python --version
if errorlevel 1 (
    echo ERREUR : Python n'est pas installe ou pas dans le PATH.
    echo Telechargez Python 3.10+ sur https://www.python.org/downloads/
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
pyinstaller avec_bukavu.spec --clean --noconfirm
if errorlevel 1 (
    echo ERREUR lors de la compilation.
    pause
    popd
    exit /b 1
)

echo.
echo === Nettoyage des fichiers temporaires ===
rmdir /s /q build 2>nul
rmdir /s /q __pycache__ 2>nul

echo.
echo ============================================================
echo  SUCCES !
echo.
echo  Votre executable se trouve dans : ..\dist\AkibaCore.exe
echo.
echo  Pour distribuer le logiciel, copiez UNIQUEMENT ce fichier
echo  dans un dossier vide. Les donnees (akibacore.db, sauvegardes,
echo  documents) seront creees automatiquement au premier lancement.
echo  Si le dossier est protege en ecriture (ex : Program Files),
echo  les donnees seront placees dans le dossier utilisateur.
echo.
echo  Identifiants initiaux : admin / admin123
echo  (changement obligatoire au premier login)
echo ============================================================
pause
popd