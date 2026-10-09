@echo off
chcp 65001 >nul
echo HexaVeil CMS — Быстрое развёртывание
echo =======================================
echo.

REM ── ЗАДАЙ ПУТЬ К ЦЕЛЕВОЙ ПАПКЕ НА ОСНОВНОМ САЙТЕ ──
set TARGET=C:\OSPanel\home\HexaCMS\public

REM Проверка: существует ли папка
if not exist "%TARGET%" (
    echo [ОШИБКА] Папка %TARGET% не найдена!
    echo Отредактируй TARGET в этом bat-файле.
    pause
    exit /b 1
)

echo Копирую файлы из %CD% в %TARGET%
echo.

REM ── PHP (контроллеры + ядро) ──
echo [PHP] controllers + core...
copy /Y admin\controllers\PostsController.php "%TARGET%\admin\controllers\PostsController.php" >nul
copy /Y core\DataGrid.php "%TARGET%\core\DataGrid.php" >nul
copy /Y core\TemplateEngine.php "%TARGET%\core\TemplateEngine.php" >nul
copy /Y core\helpers_icons.php "%TARGET%\core\helpers_icons.php" >nul
copy /Y core\routes.php "%TARGET%\core\routes.php" >nul

REM ── Шаблоны админки ──
echo [Templates] admin...
copy /Y admin\templates\dashboard.php "%TARGET%\admin\templates\dashboard.php" >nul
copy /Y admin\templates\finance\index.php "%TARGET%\admin\templates\finance\index.php" >nul
copy /Y admin\templates\theme\index.php "%TARGET%\admin\templates\theme\index.php" >nul
copy /Y admin\templates\layouts\main.php "%TARGET%\admin\templates\layouts\main.php" >nul
copy /Y admin\templates\posts\index.php "%TARGET%\admin\templates\posts\index.php" >nul

REM ── Новые шаблоны ──
echo [Templates] categories (new)...
if not exist "%TARGET%\admin\templates\posts\" mkdir "%TARGET%\admin\templates\posts\"
copy /Y admin\templates\posts\categories.php "%TARGET%\admin\templates\posts\categories.php" >nul

REM ── CSS panel ──
echo [CSS] panel...
copy /Y public\css\panel\base.css "%TARGET%\public\css\panel\base.css" >nul
copy /Y public\css\panel\components.css "%TARGET%\public\css\panel\components.css" >nul
copy /Y public\css\panel\effects.css "%TARGET%\public\css\panel\effects.css" >nul
copy /Y public\css\panel\finance.css "%TARGET%\public\css\panel\finance.css" >nul
copy /Y public\css\panel\layout.css "%TARGET%\public\css\panel\layout.css" >nul
copy /Y public\css\panel\table.css "%TARGET%\public\css\panel\table.css" >nul
copy /Y public\css\panel\themes.css "%TARGET%\public\css\panel\themes.css" >nul
copy /Y public\css\panel\tokens.css "%TARGET%\public\css\panel\tokens.css" >nul

REM ── JS ──
echo [JS] admin...
copy /Y admin\js\finance\chart.js "%TARGET%\admin\js\finance\chart.js" >nul
copy /Y admin\js\panel.js "%TARGET%\admin\js\panel.js" >nul

REM ── Тема HexaVeil ──
echo [Theme] hexaveil...
copy /Y public\hexaveil\css\style.css "%TARGET%\public\hexaveil\css\style.css" >nul
copy /Y public\hexaveil\js\star.js "%TARGET%\public\hexaveil\js\star.js" >nul
copy /Y templates\themes\hexaveil\index.php "%TARGET%\templates\themes\hexaveil\index.php" >nul
copy /Y templates\themes\hexaveil\layouts\main.php "%TARGET%\templates\themes\hexaveil\layouts\main.php" >nul
copy /Y templates\themes\hexaveil\theme.php "%TARGET%\templates\themes\hexaveil\theme.php" >nul

REM ── PROJECT.md (необязательно для сайта, но для истории) ──
copy /Y PROJECT.md "%TARGET%\PROJECT.md" >nul

echo.
echo ✅ Готово. Все 20+ файлов скопированы в %TARGET%
echo Не забудь обновить страницу через Ctrl+F5
pause