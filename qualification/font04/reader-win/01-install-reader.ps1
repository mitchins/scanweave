$ErrorActionPreference = 'Continue'
$share = '\\10.0.2.4\qemu'
$exe = 'C:\sw\AcroRdrDCx642600222031_en_US.exe'
Copy-Item "$share\in\AcroRdrDCx642600222031_en_US.exe" $exe -Force
$h = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
"installer_sha256=$h"
if ($h -ne '86e98feb3f2afa66656a85cbbc6fb71d6a3217ebf8fdc21f4d1a54d21cb45028') { 'HASH MISMATCH'; exit 2 }
$sig = Get-AuthenticodeSignature $exe
"signature_status=$($sig.Status) signer=$($sig.SignerCertificate.Subject)"
# Policy before first launch: protected mode / sandbox, updater, telemetry, upsell, first-run UI
foreach ($k in 'HKLM:\SOFTWARE\Policies\Adobe\Adobe Acrobat\DC\FeatureLockDown','HKLM:\SOFTWARE\Policies\Adobe\Acrobat Reader\DC\FeatureLockDown') {
  New-Item -Force $k | Out-Null
  foreach ($v in @{bProtectedMode=0; bEnhancedSecurityStandalone=0; bEnableProtectedModeAppContainer=0; bUpdater=0; bUsageMeasurement=0; bAcroSuppressUpsell=1; bToggleFTE=1; bToggleDCAppCenter=1; bToggleNotifications=1}.GetEnumerator()) {
    New-ItemProperty -Path $k -Name $v.Key -Value $v.Value -PropertyType DWord -Force | Out-Null }
  "policy set: $k"
}
$p = Start-Process $exe -ArgumentList '/sAll /rs /rps /msi EULA_ACCEPT=YES DISABLE_ARM_SERVICE_INSTALL=1 /L*v C:\sw\reader-install.log' -Wait -PassThru
"installer_exit=$($p.ExitCode)"
Get-ChildItem 'C:\Program Files\Adobe','C:\Program Files (x86)\Adobe' -Recurse -Include Acrobat.exe,AcroRd32.exe -ErrorAction SilentlyContinue | ForEach-Object {
  "exe=$($_.FullName) file_version=$($_.VersionInfo.FileVersion) product_version=$($_.VersionInfo.ProductVersion)" }
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object DisplayName -match 'Adobe' | ForEach-Object { "uninstall_entry=$($_.DisplayName) $($_.DisplayVersion)" }
Get-Service | Where-Object Name -match 'Adobe|Acro|ARM' | ForEach-Object { "service=$($_.Name) $($_.Status) $($_.StartType)" }
Get-ScheduledTask | Where-Object TaskName -match 'Adobe|Acro' | ForEach-Object { "task=$($_.TaskName) $($_.State)" }
Copy-Item C:\sw\reader-install.log "$share\out\reader-install.log" -Force -ErrorAction SilentlyContinue
[System.Environment]::OSVersion.VersionString
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object ProductName,DisplayVersion,CurrentBuild,UBR | Out-String)
