$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'JARVIS Assistant.lnk'

$targetPath = 'powershell.exe'
$arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$projectRoot\run_jarvis.ps1`""
$workingDirectory = $projectRoot
$iconLocation = "$env:SystemRoot\System32\shell32.dll,220"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workingDirectory
$shortcut.IconLocation = $iconLocation
$shortcut.Description = 'Launch JARVIS Assistant'
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
