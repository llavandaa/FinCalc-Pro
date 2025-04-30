#!/bin/bash

# Путь к Wine-префиксу
WINEPREFIX="$HOME/.wine-py313"
PYTHON_PATH="C:\\Python313\\python.exe"

# 1. Проверка Wine-префикса
echo "🔧 Инициализация Wine-префикса..."
WINEPREFIX=$WINEPREFIX wineboot -u

# 2. Проверка Python
if ! [[ -f "$WINEPREFIX/drive_c/Python313/python.exe" ]]; then
    echo "🚀 Скачиваем Python 3.13.3 для Windows..."
    wget -O python-installer.exe https://www.python.org/ftp/python/3.13.3/python-3.13.3-amd64.exe
    WINEPREFIX=$WINEPREFIX wine python-installer.exe
fi

# 3. Установка pip и зависимостей
echo "📦 Устанавливаем pip и зависимости..."
WINEPREFIX=$WINEPREFIX wine "$PYTHON_PATH" -m ensurepip
WINEPREFIX=$WINEPREFIX wine "$PYTHON_PATH" -m pip install --upgrade pip

# 4. Установка зависимостей из requirements.txt
WINEPREFIX=$WINEPREFIX wine "$PYTHON_PATH" -m pip install -r requirements.txt
# 5. PyInstaller
WINEPREFIX=$WINEPREFIX wine "C:\\Python313\\python.exe" -m pip install pyinstaller

