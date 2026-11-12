' Your Company • Silent Background Launcher for Windows
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c python zoho_scanner_wedge.py", 0, False
WScript.Sleep 1500
WshShell.Run "http://localhost:5000"
