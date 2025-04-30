#!/bin/bash

WINEPREFIX="$HOME/.wine-py313"
PYTHON_PATH="C:\\Python313\\python.exe"
PYINSTALLER_PATH="C:\\Python313\\Scripts\\pyinstaller.exe"

# Создаём директорию для сборки, если её нет
mkdir -p "$WINEPREFIX/drive_c/build"

# Копируем main.py и icon.ico в Wine
cp main.py icon.ico "$WINEPREFIX/drive_c/build/"

# Сборка
echo "🛠 Собираем FinCalcPro.exe..."
WINEPREFIX=$WINEPREFIX wine "$PYINSTALLER_PATH" \
  --onefile --noconsole --name="FinCalc Pro v1.4.6-2r" --icon=C:/build/icon.ico C:/build/main.py
