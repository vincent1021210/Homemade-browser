# 在純英文目錄建置安裝檔，避免 NSIS 與 WebEngine 碰到中文路徑。
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $env:LOCALAPPDATA "LocalBrowser\installer-src"
$nsisRoot = Join-Path $env:LOCALAPPDATA "LocalBrowser\nsis"
$python = Join-Path $env:LOCALAPPDATA "local-browser-venv\Scripts\python.exe"
$pynsist = Join-Path $env:LOCALAPPDATA "local-browser-venv\Scripts\pynsist.exe"

if (-not (Test-Path (Join-Path $nsisRoot "makensis.exe"))) {
    $zip = Join-Path $env:TEMP "nsis-3.10.zip"
    Write-Host "Downloading NSIS..."
    curl.exe -L --fail -o $zip "https://downloads.sourceforge.net/project/nsis/NSIS%203/3.10/nsis-3.10.zip"
    if (Test-Path $nsisRoot) { Remove-Item -Recurse -Force $nsisRoot }
    Expand-Archive -Path $zip -DestinationPath (Split-Path $nsisRoot) -Force
    $extracted = Join-Path (Split-Path $nsisRoot) "nsis-3.10"
    if (Test-Path $extracted) {
        if (Test-Path $nsisRoot) { Remove-Item -Recurse -Force $nsisRoot }
        Rename-Item $extracted $nsisRoot
    }
}

if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Path $stage | Out-Null
$names = @(
    "main.py", "engine.py", "home.py", "location.py",
    "store.py", "style.py", "tab.py", "window.py"
)
foreach ($name in $names) {
    Copy-Item (Join-Path $root $name) (Join-Path $stage $name)
}
Copy-Item (Join-Path $PSScriptRoot "pynsist.cfg") (Join-Path $stage "pynsist.cfg")
Copy-Item (Join-Path $PSScriptRoot "pyapp_user.nsi") (Join-Path $stage "pyapp_user.nsi")
Copy-Item (Join-Path $PSScriptRoot "browser.ico") (Join-Path $stage "browser.ico")

$env:PYTHONUTF8 = "1"
$env:PATH = "$nsisRoot;" + $env:PATH
Push-Location $stage
try {
    & $pynsist "pynsist.cfg" --no-makensis
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $nsi = Join-Path $stage "build\installer.nsi"
    $bytes = [System.IO.File]::ReadAllBytes($nsi)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF) {
        $bom = [byte[]](0xEF, 0xBB, 0xBF)
        [System.IO.File]::WriteAllBytes($nsi, $bom + $bytes)
    }
    & (Join-Path $nsisRoot "makensis.exe") $nsi
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

$setup = Join-Path $stage "build\LocalBrowser-Setup.exe"
Write-Host "SETUP $setup"
