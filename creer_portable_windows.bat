@echo off
REM ============================================================
REM  AkibaCore v2.2.0 - Creation de la version PORTABLE Windows
REM  A executer sur Windows APRES build_windows.bat (dist\AkibaCore.exe
REM  doit exister).
REM
REM  Produit :  AkibaCore_Portable_v2.2.0_Windows.zip
REM
REM  La structure portable cree d'abord les dossiers de donnees.
REM  L'application les recree automatiquement si absents au lancement.
REM ============================================================

setlocal
cd /d "%~dp0"

echo ============================================================
echo  AkibaCore v2.2.0 - Assemblage de la version PORTABLE
echo ============================================================
echo.

if not exist "dist\AkibaCore.exe" (
    echo ERREUR : dist\AkibaCore.exe introuvable.
    echo Lancez d'abord : build_windows.bat
    pause
    exit /b 1
)

set "PORTABLE=AkibaCore_Portable"
set "DEST=%PORTABLE%\AkibaCore"

echo === Nettoyage de l'ancien dossier ===
if exist "%PORTABLE%" rmdir /s /q "%PORTABLE%"

echo === Copie de l'executable ===
mkdir "%DEST%"
copy /y "dist\AkibaCore.exe" "%DEST%\AkibaCore.exe" >nul

echo === Creation des dossiers de donnees ===
mkdir "%DEST%\data"         2>nul
mkdir "%DEST%\sauvegardes"  2>nul
mkdir "%DEST%\documents"    2>nul
mkdir "%DEST%\modeles"      2>nul
mkdir "%DEST%\exports"      2>nul
mkdir "%DEST%\logs"         2>nul

echo === Copie de la documentation ===
if exist "GUIDE_INSTALLATION_WINDOWS.txt" copy /y "GUIDE_INSTALLATION_WINDOWS.txt" "%PORTABLE%\" >nul 2>&1
if exist "GUIDE_UTILISATEUR.txt" copy /y "GUIDE_UTILISATEUR.txt" "%PORTABLE%\" >nul 2>&1
if exist "CHANGELOG.md" copy /y "CHANGELOG.md" "%PORTABLE%\" >nul 2>&1

echo === Compression ZIP ===
if exist "AkibaCore_Portable_v2.2.0_Windows.zip" del /q "AkibaCore_Portable_v2.2.0_Windows.zip"

powershell -NoProfile -Command ^
  "Compress-Archive -Path '%PORTABLE%\*' -DestinationPath 'AkibaCore_Portable_v2.2.0_Windows.zip' -Force"

if errorlevel 1 (
    echo ERREUR lors de la creation du ZIP.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SUCCES !
echo.
echo  Version portable creee : AkibaCore_Portable_v2.2.0_Windows.zip
echo.
echo  Pour l'utiliser :
echo   1. Decompressez le ZIP n'importe ou (ex : Documents)
echo   2. Double-cliquez sur AkibaCore.exe
echo   3. Les donnees sont conservees DANS le dossier portable.
echo ============================================================
pause
endlocal
