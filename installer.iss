[Setup]
AppId={{C3B4A52D-69A7-47C8-9A1D-8F2D6C45B6A1}
AppName=Viral Clips Generator
AppVersion=0.1.0
AppPublisher=Viral Clips Generator
DefaultDirName={autopf}\Viral Clips Generator
DefaultGroupName=Viral Clips Generator
OutputDir=Output
OutputBaseFilename=ViralClipsGenerator_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
[Files]
Source: "dist\ViralClipsGenerator\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Viral Clips Generator"; Filename: "{app}\ViralClipsGenerator.exe"
Name: "{autodesktop}\Viral Clips Generator"; Filename: "{app}\ViralClipsGenerator.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
[Run]
Filename: "{app}\ViralClipsGenerator.exe"; Description: "Abrir Viral Clips Generator"; Flags: postinstall nowait skipifsilent
