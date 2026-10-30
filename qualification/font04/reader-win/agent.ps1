# Polls the QEMU SMB share for job scripts and runs them in this interactive session.
$share = '\\10.0.2.4\qemu'
while ($true) {
  try {
    if (Test-Path "$share\jobs") {
      Set-Content "$share\out\heartbeat.txt" (Get-Date -Format o) -ErrorAction SilentlyContinue
      foreach ($j in Get-ChildItem "$share\jobs" -Filter *.ps1 | Sort-Object Name) {
        $name = $j.BaseName
        $local = "C:\sw\jobs\$($j.Name)"
        New-Item -ItemType Directory -Force C:\sw\jobs | Out-Null
        Move-Item $j.FullName $local -Force
        $log = "C:\sw\jobs\$name.log"
        $proc = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$local`"" -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
        while (-not $proc.WaitForExit(2000)) {
          if (Test-Path "$share\kill") { Remove-Item "$share\kill" -Force; & taskkill.exe /T /F /PID $proc.Id | Out-Null }
        }
        Copy-Item $log "$share\out\$name.log" -Force
        Copy-Item "$log.err" "$share\out\$name.err" -Force
        Set-Content "$share\out\$name.done" $proc.ExitCode
      }
    }
  } catch { Add-Content C:\sw\agent-errors.log ("{0} {1}" -f (Get-Date -Format o), $_) }
  Start-Sleep -Seconds 3
}
