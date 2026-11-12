# Собирает портативную папку EasyEDA2KiCad и ZIP для GitHub Release.
# Использование:
#   .\build.ps1            -> dist\EasyEDA2KiCad\ + EasyEDA2KiCad-portable.zip
#   .\build.ps1 -OneFile   -> dist\EasyEDA2KiCad.exe + ZIP

param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Создаю виртуальное окружение..."
    python -m venv .venv
}

Write-Host "Устанавливаю зависимости..."
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt -r requirements-dev.txt

$icon = (Resolve-Path "icon.ico").Path
$mode = if ($OneFile) { "--onefile" } else { "--onedir" }

Write-Host "Собираю $mode ..."
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

& $python -m PyInstaller --noconfirm --clean $mode --windowed `
    --icon $icon --add-data "$icon;." `
    --name EasyEDA2KiCad `
    --distpath dist --workpath build --specpath build app.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller завершился с ошибкой"
}

$appDir = if ($OneFile) { "dist" } else { "dist\EasyEDA2KiCad" }

Write-Host "Добавляю документацию..."
Copy-Item "README.md" $appDir -Force
Copy-Item "README.ru.md" $appDir -Force
Copy-Item "LICENSE" $appDir -Force
Copy-Item "THIRD_PARTY_NOTICES.md" $appDir -Force
Copy-Item "docs" $appDir -Recurse -Force

$zip = Join-Path $PSScriptRoot "EasyEDA2KiCad-portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

if ($OneFile) {
    Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zip -CompressionLevel Optimal
} else {
    Compress-Archive -Path $appDir -DestinationPath $zip -CompressionLevel Optimal
}

$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host ""
Write-Host "Готово: $zip ($sizeMb МБ)"
