#define MyAppName "Total Hunter"
#define MyAppVersion "1.1.3"
#define MyAppPublisher "Total Hunter"
#define MyAppURL "https://total-hunter.com"
#define MyAppExeName "TotalHunter.exe"

[Setup]
AppId={{A7F3B2C1-D4E5-4F6A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=TotalHunter_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; Windows 10 x64 минимум — Python 3.13 + PyTorch не запускаются ниже
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
; Автовыбор языка по локали системы (показывает диалог только если неоднозначно)
ShowLanguageDialog=auto

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; VC++ Runtime — устанавливается только если нет
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
; Все файлы программы
Source: "dist\TotalHunter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Установить VC++ если не установлен (проверка через реестр)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
  Check: VCRedistNeedsInstall; StatusMsg: "Установка Visual C++ Runtime..."; \
  Flags: waituntilterminated
; Запустить программу после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[Code]
// ─── Проверки совместимости ───────────────────────────────────────────────

function InitializeSetup: Boolean;
var
  OSMajor, OSMinor, OSBuild: Cardinal;
  IsWow64: Boolean;
  Msg: String;
begin
  Result := True;

  // Проверка: 64-bit Windows
  IsWow64 := IsWin64;
  if not IsWow64 then
  begin
    if ActiveLanguage = 'russian' then
      Msg := 'Total Hunter требует 64-разрядную версию Windows.' + #13#10 +
             'Ваша система: 32-bit. Установка невозможна.'
    else
      Msg := 'Total Hunter requires 64-bit Windows.' + #13#10 +
             'Your system is 32-bit. Installation cannot continue.';
    MsgBox(Msg, mbCriticalError, MB_OK);
    Result := False;
    Exit;
  end;

  // Проверка: Windows 10+ (build 10240+)
  // MinVersion=10.0 уже блокирует Inno Setup, но добавляем явную проверку с читаемым сообщением
  if not RegQueryDWordValue(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'CurrentMajorVersionNumber', OSMajor) then
    OSMajor := 0;

  if OSMajor < 10 then
  begin
    if ActiveLanguage = 'russian' then
      Msg := 'Total Hunter требует Windows 10 или новее.' + #13#10 +
             'Причина: бот использует Python 3.13 и PyTorch, которые' + #13#10 +
             'не поддерживают Windows 7/8/8.1.' + #13#10#13#10 +
             'Обновите операционную систему до Windows 10 (бесплатно).'
    else
      Msg := 'Total Hunter requires Windows 10 or later.' + #13#10 +
             'Reason: the bot uses Python 3.13 and PyTorch, which do' + #13#10 +
             'not support Windows 7/8/8.1.' + #13#10#13#10 +
             'Please upgrade to Windows 10 (free upgrade available).';
    MsgBox(Msg, mbCriticalError, MB_OK);
    Result := False;
    Exit;
  end;
end;

// ─── Проверка VC++ ────────────────────────────────────────────────────────

function VCRedistNeedsInstall: Boolean;
var
  sVersion: String;
begin
  // Проверяем VC++ 2015-2022 x64 (14.29+ = Visual Studio 2022)
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
    'Version', sVersion) then
  begin
    Result := (sVersion < 'v14.29');
  end
  else
    Result := True; // не установлен — ставим
end;
