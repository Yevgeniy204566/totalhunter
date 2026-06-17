@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================
echo   BattleBot ^-^> Google Drive Symlink Creator
echo ================================================
echo.

:: Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Требуются права Администратора!
    echo.
    echo Закройте окно и запустите файл правой кнопкой
    echo мыши -^> "Запустить от имени администратора"
    echo.
    pause
    exit /b 1
)

echo [OK] Права Администратора подтверждены.
echo.

set SOURCE=C:\BattleBot\docs
set TARGET=H:\Мой диск\Gemini_Sync

:: Check source folder exists
if not exist "%SOURCE%" (
    echo [ERROR] Папка источник не найдена: %SOURCE%
    pause
    exit /b 1
)

:: Check if target exists
if exist "%TARGET%" (
    echo [!] Папка уже существует: %TARGET%
    echo.
    set /p CHOICE="Удалить и пересоздать? (y/n): "
    if /i "!CHOICE!"=="y" (
        rmdir /s /q "%TARGET%"
        echo [OK] Старая папка удалена.
    ) else (
        echo [OK] Оставляем папку, добавляем ссылки...
    )
    echo.
)

:: Create target folder
if not exist "%TARGET%" (
    mkdir "%TARGET%"
    echo [OK] Папка создана: %TARGET%
    echo.
)

:: Create symlinks for 4 files
echo Создаём символические ссылки...
echo.

mklink "%TARGET%\gemini_buffer.md" "%SOURCE%\gemini_buffer.md"
if %errorLevel% neq 0 echo [ERROR] gemini_buffer.md

mklink "%TARGET%\GKB_Gemini.md" "%SOURCE%\GKB_Gemini.md"
if %errorLevel% neq 0 echo [ERROR] GKB_Gemini.md

mklink "%TARGET%\TECH_PASSPORT.md" "%SOURCE%\TECH_PASSPORT.md"
if %errorLevel% neq 0 echo [ERROR] TECH_PASSPORT.md

mklink "%TARGET%\Total Hunter global project.md" "%SOURCE%\Total Hunter global project.md"
if %errorLevel% neq 0 echo [ERROR] Total Hunter global project.md

echo.
echo ================================================
echo   Готово! Файлы зеркалированы в Google Drive
echo   %TARGET%
echo ================================================
echo.
pause
