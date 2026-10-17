# 在项目根目录生成 Windows 目录版程序：dist\EyeGuard\EyeGuard.exe
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m pip install pyinstaller
python -m PyInstaller packaging\eyeguard.spec --noconfirm --clean
Write-Host "完成：dist\EyeGuard\EyeGuard.exe"
