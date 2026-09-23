Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root
sh.Environment("Process")("PYTHONUTF8") = "1"
sh.Environment("Process")("PYTHONPATH") = root & "\_app"

On Error Resume Next
Set svc = GetObject("winmgmts:\\.\root\cimv2")
Set procs = svc.ExecQuery("Select ProcessId,CommandLine,Name from Win32_Process where Name='pythonw.exe' or Name='python.exe' or Name='AuraUI.exe'")
For Each p In procs
  cmd = LCase("" & p.CommandLine)
  nm = LCase("" & p.Name)
  If InStr(cmd, "web_main.py") > 0 Or nm = "auraui.exe" Then
    sh.Run "taskkill /F /PID " & p.ProcessId, 0, True
  End If
Next
On Error GoTo 0
WScript.Sleep 500
ui = root & "\_app\webui\web_main.py"
exe = root & "\AuraUI.exe"
If fso.FileExists(exe) Then
  sh.Run chr(34) & exe & chr(34) & " " & chr(34) & ui & chr(34), 1, False
Else
  sh.Run chr(34) & "pythonw" & chr(34) & " " & chr(34) & ui & chr(34), 1, False
End If
