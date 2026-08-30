@echo off
REM ============================================================
REM  AkibaCore v2.2.0 - Assemblage release\ (Windows)
REM  A executer APRES build_windows.bat (+ creer_portable_windows.bat)
REM ============================================================
setlocal
cd /d "%~dp0"
REM On travaille depuis la racine du projet (parents de setup_windows\)
pushd "%~dp0.."

echo === Assemblage du dossier release\ ===
if not exist "release" mkdir "release"

for %%f in (CHANGELOG.md GUIDE_UTILISATEUR.md GUIDE_ADMINISTRATEUR.md GUIDE_INSTALLATION_WINDOWS.md RAPPORT_FINAL_V2.2.0.md RELEASE_NOTES_v2.0.0.md README.md) do (
  if exist "%%f" copy /y "%%f" "release\" >nul && echo   + %%f
)

if exist "GUIDE_INSTALLATION_WINDOWS.md" copy /y "GUIDE_INSTALLATION_WINDOWS.md" "release\GUIDE_INSTALLATION_WINDOWS.txt" >nul

if exist "AkibaCore_Setup_v2.2.0_Windows_x64.exe" (
  copy /y "AkibaCore_Setup_v2.2.0_Windows_x64.exe" "release\" >nul && echo   + installateur
)
if exist "AkibaCore_Portable_v2.2.0_Windows.zip" (
  copy /y "AkibaCore_Portable_v2.2.0_Windows.zip" "release\" >nul && echo   + portable
)

echo.
echo === Generation de SHA256SUMS.txt ===
cd release
if exist SHA256SUMS.txt del /q SHA256SUMS.txt
powershell -NoProfile -Command ^
  "Get-ChildItem -File | ForEach-Object { Get-FileHash $_.FullName -Algorithm SHA256 | ForEach-Object { \"$($_.Hash.ToLower())  $($_.Path.Substring($_.Path.LastIndexOf('\')+1))\" } } | Set-Content SHA256SUMS.txt"
cd ..

echo.
echo Dossier release\ pret.
pause
popd
endlocal
