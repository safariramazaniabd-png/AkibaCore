; ============================================================
;  AkibaCore v2.2.0 - Script d'installation Windows (Inno Setup)
; ============================================================
;  Comment construire l'installateur :
;    1. Sur Windows : lancez build_windows.bat (dans ce dossier,
;       produit ..\dist\AkibaCore.exe)
;    2. Ouvrez ce fichier dans Inno Setup (gratuit : https://jrsoftware.org/isinfo.php)
;    3. Menu : Build > Compile
;    4. Le resultat est :  ..\release\AkibaCore_Setup_v2.2.0_Windows_x64.exe
; ============================================================
;
;  IMPORTANT — DONNEES UTILISATEUR :
;  L'application est installee dans "Program Files" (protege en ecriture).
;  L'executable detecte automatiquement ce cas et place la base, les
;  sauvegardes et les documents dans le dossier UTILISATEUR
;  (%LOCALAPPDATA%\AkibaCore). La desinstallation ne supprime JAMAIS
;  ces donnees utilisateur.

#define MyAppName "AkibaCore"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "AkibaCore"
#define MyAppExeName "AkibaCore.exe"
#define MyAppAssocName MyAppName + " Data"

[Setup]
AppId={{8F2C6E9A-4E3B-4D1C-9C5A-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=AkibaCore_Setup_v{#MyAppVersion}_Windows_x64
SetupIconFile=..\AkibaCore.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; La desinstallation ne touche PAS au dossier de donnees utilisateur.
[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\AkibaCore.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AkibaCore.ico"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AkibaCore.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Message d'information sur les donnees : montre ou elles sont conservees.
function InitializeSetup(): Boolean;
begin
  MsgBox('AkibaCore conservera vos donnees dans le dossier utilisateur (jamais dans Program Files).' + #13#10 + 'La desinstallation ne supprime pas vos donnees.', mbInformation, MB_OK);
  Result := True;
end;
