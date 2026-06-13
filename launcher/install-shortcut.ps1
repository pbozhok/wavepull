$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'WavePull.lnk'

$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'cmd.exe'
$shortcut.Arguments = '/c "' + $PSScriptRoot + '\start-wavepull.bat"'
$shortcut.WorkingDirectory = Split-Path $PSScriptRoot -Parent
$shortcut.Description = 'Launch WavePull'
$shortcut.IconLocation = $PSScriptRoot + '\wavepull.ico,0'
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "WavePull shortcut created at: $shortcutPath"
