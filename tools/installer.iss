; (UTF-8 BOM 으로 저장한다 - 없으면 Inno Setup 이 한글을 깨뜨린다)
; 윈도우 설치 파일 (Inno Setup). tools/build.py 가 부른다:
;   iscc /DAppVersion=0.1.0 /DSourceDir=dist\MyUNi /DOutputDir=dist /DIconFile=icon.ico tools\installer.iss
;
; 관리자 권한 없이 사용자 폴더(%LOCALAPPDATA%\Programs\MyUNi)에 깐다. 학교 · PC방처럼 관리자 권한이
; 없는 컴퓨터에서도 깔리고, UAC 창도 안 뜬다.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F0B1D2E-4C1A-4E7B-9C55-3B1F6A9D2E71}
AppName=MyUNi
AppVersion={#AppVersion}
AppPublisher=MyUNi
AppPublisherURL=https://qkrsj.github.io/myuni/
DefaultDirName={localappdata}\Programs\MyUNi
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=MyUNi-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\MyUNi.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 켜져 있는 MyUNi 를 닫고 덮어쓴다 (업데이트할 때)
CloseApplications=yes
RestartApplications=no

[Languages]
; Korean.isl 이 없는 Inno Setup 판이면 영어 화면으로 만든다
#if FileExists(AddBackslash(CompilerPath) + "Languages\Korean.isl")
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#else
Name: "english"; MessagesFile: "compiler:Default.isl"
#endif

[Tasks]
Name: "startup"; Description: "윈도우를 켤 때 MyUNi 도 같이 켜기"; GroupDescription: "추가 설정:"
Name: "desktopicon"; Description: "바탕화면에 바로 가기 만들기"; GroupDescription: "추가 설정:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\MyUNi"; Filename: "{app}\MyUNi.exe"
Name: "{userdesktop}\MyUNi"; Filename: "{app}\MyUNi.exe"; Tasks: desktopicon
Name: "{userstartup}\MyUNi"; Filename: "{app}\MyUNi.exe"; Tasks: startup

[Run]
Filename: "{app}\MyUNi.exe"; Description: "MyUNi 실행하기"; Flags: nowait postinstall skipifsilent
