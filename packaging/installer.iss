; Inno Setup 脚本。通过 dev.ps1 installer 调用，版本号由 /DAppVersion 传入。
; 装到用户目录而非 Program Files：程序会在 exe 旁边写 data\，普通用户目录可写。
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8F3B6C1E-5B7A-4D0A-9E1D-3A7C2F5B9D01}
AppName=护眼计时
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\EyeGuard
DefaultGroupName=护眼计时
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=EyeGuard-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\EyeGuard.exe

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; Flags: unchecked

[Files]
Source: "..\dist\EyeGuard\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\护眼计时"; Filename: "{app}\EyeGuard.exe"
Name: "{userdesktop}\护眼计时"; Filename: "{app}\EyeGuard.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EyeGuard.exe"; Description: "立即运行"; Flags: nowait postinstall skipifsilent
