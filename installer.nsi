!include "MUI2.nsh"

Name "POS System"
OutFile "POS-System-Setup.exe"
InstallDir "$PROGRAMFILES\POS System"

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy the executable
    File "dist\pos_launcher.exe"
    
    ; Copy required directories
    File /r "templates"
    File /r "static"
    File /r "migrations"
    
    ; Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\POS System"
    CreateShortcut "$SMPROGRAMS\POS System\POS System.lnk" "$INSTDIR\pos_launcher.exe"
    CreateShortcut "$DESKTOP\POS System.lnk" "$INSTDIR\pos_launcher.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Add uninstall information to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\POS System" \
                     "DisplayName" "POS System"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\POS System" \
                     "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
SectionEnd

Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\pos_launcher.exe"
    RMDir /r "$INSTDIR\templates"
    RMDir /r "$INSTDIR\static"
    RMDir /r "$INSTDIR\migrations"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\POS System\POS System.lnk"
    RMDir "$SMPROGRAMS\POS System"
    Delete "$DESKTOP\POS System.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\POS System"
    
    ; Remove install directory
    RMDir "$INSTDIR"
SectionEnd 