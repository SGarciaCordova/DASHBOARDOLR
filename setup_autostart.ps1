$WshShell = New-Object -comObject WScript.Shell
$StartupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupPath\Iniciar Dashboard.lnk"
$TargetScript = "$PSScriptRoot\Iniciar_Dashboard.ps1"
$WorkDir = $PSScriptRoot

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$TargetScript`" -WindowStyle Minimized"
$Shortcut.WorkingDirectory = $WorkDir
$Shortcut.WindowStyle = 7 # Minimized
$Shortcut.Description = "Auto-start Antigravity Dashboard"
$Shortcut.Save()

Write-Host "Shortcut created successfully at: $ShortcutPath" -ForegroundColor Green
