' Create Desktop Shortcut for Smart Outbound Dialer
' VBScript version (works without PowerShell)

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get script directory
ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Get desktop path
DesktopPath = WshShell.SpecialFolders("Desktop")
ShortcutPath = DesktopPath & "\Smart Outbound Dialer.lnk"

' Find Python executable
PythonPath = "python.exe"

' Try to find Python in common locations
If Not fso.FileExists(PythonPath) Then
    ' Try Python in PATH
    On Error Resume Next
    PythonPath = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\python.exe")
    If Not fso.FileExists(PythonPath) Then
        PythonPath = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python311\python.exe")
    End If
    If Not fso.FileExists(PythonPath) Then
        PythonPath = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python310\python.exe")
    End If
    If Not fso.FileExists(PythonPath) Then
        PythonPath = "python.exe"  ' Fallback to PATH
    End If
    On Error Goto 0
End If

' Create shortcut
Set Shortcut = WshShell.CreateShortcut(ShortcutPath)
Shortcut.TargetPath = PythonPath
Shortcut.Arguments = """" & ScriptDir & "\desktop_app.py"""
Shortcut.WorkingDirectory = ScriptDir
Shortcut.Description = "Smart Outbound Dialer - VoIP Calling System"
Shortcut.WindowStyle = 1

' Set icon if it exists
IconPath = ScriptDir & "\app_icon.ico"
If fso.FileExists(IconPath) Then
    Shortcut.IconLocation = IconPath
End If

' Save shortcut
Shortcut.Save

' Show success message
WScript.Echo "Desktop Shortcut Created Successfully!" & vbCrLf & vbCrLf & _
             "Location: " & ShortcutPath & vbCrLf & vbCrLf & _
             "You can now double-click 'Smart Outbound Dialer' on your desktop!"
