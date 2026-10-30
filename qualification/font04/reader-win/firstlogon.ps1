$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force C:\sw | Out-Null
Start-Transcript C:\sw\firstlogon.log
Copy-Item (Join-Path $PSScriptRoot 'agent.ps1') C:\sw\agent.ps1 -Force
# SMB client: allow QEMU's guest-only share
Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -RequireSecuritySignature $false -Confirm:$false
reg add HKLM\SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation /v AllowInsecureGuestAuth /t REG_DWORD /d 1 /f
# Keep the desktop awake and unlocked
powercfg /change monitor-timeout-ac 0; powercfg /change standby-timeout-ac 0; powercfg /change hibernate-timeout-ac 0
reg add HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization /v NoLockScreen /t REG_DWORD /d 1 /f
reg add "HKCU\Control Panel\Desktop" /v ScreenSaveActive /t REG_SZ /d 0 /f
# No Windows Update during the check
reg add HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU /v NoAutoUpdate /t REG_DWORD /d 1 /f
# Agent runs in the interactive session at every logon
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\sw\agent.ps1'
$t = New-ScheduledTaskTrigger -AtLogOn -User tester
$p = New-ScheduledTaskPrincipal -UserId tester -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName swagent -Action $a -Trigger $t -Principal $p -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -AllowStartIfOnBatteries) -Force
Start-ScheduledTask -TaskName swagent
Stop-Transcript
