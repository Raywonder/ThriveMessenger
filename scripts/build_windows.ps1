param(
    [string]$OutputDir = "dist-windows"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python versionfile.py
python -m PyInstaller --clean --noconfirm --windowed --version-file=vdata.txt --name "thrive_messenger" --distpath $OutputDir main.py

$AppDir = Join-Path $Root (Join-Path $OutputDir "thrive_messenger")
if (!(Test-Path $AppDir)) {
    throw "PyInstaller output not found: $AppDir"
}

New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "sounds") | Out-Null
Copy-Item -Recurse -Force "sounds\*" (Join-Path $AppDir "sounds")
Copy-Item -Force "client.conf" (Join-Path $AppDir "client.conf")

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$PortableZip = Join-Path $OutputDir "thrive_messenger.zip"
if (Test-Path $PortableZip) {
    Remove-Item -Force $PortableZip
}
Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $PortableZip -Force

Write-Host "Portable package created: $PortableZip"
