# 开发 / 调试 / 打包入口。用法：.\dev.ps1 <任务>
param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "run", "debug", "smoke", "test", "build", "zip", "installer", "release", "clean")]
    [string]$Task = "run"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Run($exe, $a) { & $exe @a; if ($LASTEXITCODE) { throw "$exe 失败（退出码 $LASTEXITCODE）" } }
function Version { (python -c "import eyeguard; print(eyeguard.__version__)").Trim() }

switch ($Task) {
    "setup"     { Run python @("-m", "pip", "install", "-r", "requirements.txt") }
    "run"       { Run python @("run.py") }
    "debug"     { Run python @("run.py", "--debug") }                  # 日志打到控制台
    "smoke"     { Run python @("run.py", "--smoke") }
    "test"      { Run python @("-m", "unittest", "discover", "-s", "tests") }
    "build"     { & packaging\build_windows.ps1 }                      # dist\EyeGuard\EyeGuard.exe
    "zip" {                                                            # 便携版 zip
        & packaging\build_windows.ps1
        $out = "dist\EyeGuard-$(Version)-win64.zip"
        Compress-Archive dist\EyeGuard -DestinationPath $out -Force
        Write-Host "完成：$out"
    }
    "installer" {                                                      # 安装包 exe，需要 Inno Setup 6
        $iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
        if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
        if (-not (Test-Path $iscc)) { throw "未找到 ISCC.exe。请先安装 Inno Setup 6：winget install JRSoftware.InnoSetup" }
        & packaging\build_windows.ps1
        Run $iscc @("/DAppVersion=$(Version)", "packaging\installer.iss")
        Write-Host "完成：dist\EyeGuard-Setup-$(Version).exe"
    }
    "release" {                                                        # 发布到 GitHub Release，需要 gh 并已登录
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "未找到 gh。请先安装并登录：winget install GitHub.cli; gh auth login" }
        & $PSCommandPath zip
        $v = Version
        $files = @("dist\EyeGuard-$v-win64.zip") + @(Get-Item "dist\EyeGuard-Setup-$v.exe" -ErrorAction SilentlyContinue | % FullName)  # 有安装包就一起发
        Run gh (@("release", "create", "v$v") + $files + @("--title", "v$v", "--generate-notes"))
    }
    "clean"     { Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue }
}
