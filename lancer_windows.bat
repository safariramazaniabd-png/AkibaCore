@echo off
chcp 65001 > nul
title AkibaCore — Démarrage
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║        AkibaCore v2.0 — Démarrage       ║
echo  ╚══════════════════════════════════════════╝
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo  ERREUR : Python n'est pas installé ou pas dans PATH.
    echo  Téléchargez Python sur https://python.org
    pause
    exit /b 1
)

echo  Lancement de l'application...
python main.py
if errorlevel 1 (
    echo.
    echo  Une erreur s'est produite. Contactez le support technique.
    pause
)
