[Setup]
AppName=VirtualMic Server
AppVersion=2.0
DefaultDirName={autopf}\VirtualMic Server
DefaultGroupName=VirtualMic Server
OutputDir=D:\Android Projects\VirtualMic\dist
OutputBaseFilename=VirtualMic_Installer
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=D:\Android Projects\VirtualMic\icon.ico

[Files]
Source: "D:\Android Projects\VirtualMic\dist\server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Android Projects\VirtualMic\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Android Projects\VirtualMic\VBCable\*"; DestDir: "{tmp}\VBCable"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VirtualMic Server"; Filename: "{app}\server.exe"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\VirtualMic Server"; Filename: "{app}\server.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
; Run the VBCable installer silently
Filename: "{tmp}\VBCable\VBCABLE_Setup_x64.exe"; Parameters: "-i -h"; WorkingDir: "{tmp}\VBCable"; Flags: waituntilterminated runascurrentuser; Check: Is64BitInstallMode
Filename: "{tmp}\VBCable\VBCABLE_Setup.exe"; Parameters: "-i -h"; WorkingDir: "{tmp}\VBCable"; Flags: waituntilterminated runascurrentuser; Check: not Is64BitInstallMode
; Launch the app at the end
Filename: "{app}\server.exe"; Description: "Launch VirtualMic Server"; Flags: nowait postinstall skipifsilent
