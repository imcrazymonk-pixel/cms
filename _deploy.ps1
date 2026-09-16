<#
.SYNOPSIS
    HexaVeil CMS — FTP развёртывание всех изменённых файлов
.DESCRIPTION
    Загружает 20+ файлов на сервер по FTP.
    Использует встроенный .NET FTP-клиент Windows (System.Net.WebClient).
.NOTES
    ЗАПОЛНИ ПЕРЕМЕННЫЕ $ftpHost, $ftpUser, $ftpPass, $remoteRoot ПЕРЕД ЗАПУСКОМ
#>

# ── FTP ДАННЫЕ ──
$ftpHost    = "hexaveil.xyz"             # SprintHost — пробуем через домен
$ftpPort    = 21                         # Стандартный FTP порт
$ftpUser    = "a0211297"                # Логин
$ftpPass    = "mucakianti"              # Пароль
$remoteRoot = "/domains/hexaveil.xyz/public_html"  # Корень сайта

# ── Локальный корень проекта ──
$localRoot  = "C:\Users\Andre\Desktop\VPN\NewWeb"

# ── Список файлов для загрузки ──
$files = @( ... ) # остаётся как есть

# ── Список файлов для загрузки (относительные пути) ──
$files = @(
    # PHP — ядро
    "core\DataGrid.php"
    "core\TemplateEngine.php"
    "core\helpers_icons.php"
    "core\routes.php"
    
    # PHP — контроллеры
    "admin\controllers\PostsController.php"
    
    # Шаблоны админки
    "admin\templates\dashboard.php"
    "admin\templates\finance\index.php"
    "admin\templates\theme\index.php"
    "admin\templates\layouts\main.php"
    "admin\templates\posts\index.php"
    "admin\templates\posts\categories.php"
    
    # JS
    "admin\js\finance\chart.js"
    "admin\js\panel.js"
    
    # CSS панели
    "public\css\panel\base.css"
    "public\css\panel\components.css"
    "public\css\panel\effects.css"
    "public\css\panel\finance.css"
    "public\css\panel\layout.css"
    "public\css\panel\table.css"
    "public\css\panel\themes.css"
    "public\css\panel\tokens.css"
    
    # Тема HexaVeil
    "public\hexaveil\css\style.css"
    "public\hexaveil\js\star.js"
    "templates\themes\hexaveil\index.php"
    "templates\themes\hexaveil\layouts\main.php"
    "templates\themes\hexaveil\theme.php"
)

$count = 0
$errors = 0

foreach ($relPath in $files) {
    $localFile  = Join-Path $localRoot $relPath
    $remoteFile = ($remoteRoot + "/" + ($relPath -replace '\\', '/')).Replace('//', '/')
    
    if (!(Test-Path $localFile)) {
        Write-Host "[ПРОПУСК] Не найден: $relPath" -ForegroundColor Yellow
        continue
    }
    
    try {
        $ftpUrl = "ftp://$ftpHost$remoteFile"
        
        # Создаём FTP-запрос с passive mode
        $request = [System.Net.FtpWebRequest]::Create($ftpUrl)
        $request.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
        $request.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
        $request.UsePassive = $true
        $request.UseBinary = $true
        $request.KeepAlive = $false
        $request.EnableSsl = $false
        
        # Читаем файл и загружаем
        $fileBytes = [System.IO.File]::ReadAllBytes($localFile)
        $request.ContentLength = $fileBytes.Length
        $stream = $request.GetRequestStream()
        $stream.Write($fileBytes, 0, $fileBytes.Length)
        $stream.Close()
        
        $response = $request.GetResponse()
        $response.Close()
        
        $count++
        Write-Host "[OK] $relPath" -ForegroundColor Green
    } catch {
        Write-Host "[ОШИБКА] $relPath : $_" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Загружено: $count из $($files.Count)" -ForegroundColor Green
if ($errors -gt 0) { Write-Host "Ошибок: $errors" -ForegroundColor Red }
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan