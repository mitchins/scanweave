. \\10.0.2.4\qemu\in\swlib.ps1
$ErrorActionPreference = 'Continue'
$crops = Get-Content \\10.0.2.4\qemu\in\crops.json -Raw | ConvertFrom-Json
$pdfs = [ordered]@{
  'financial-default' = @('financial', 13); 'financial-cover-2.0' = @('financial', 13); 'financial-cover-1.5' = @('financial', 13)
  'mixed-default' = @('mixed', 2); 'mixed-cover-2.0' = @('mixed', 2) }
$words = @{
  financial = 'labor','supplies','TOWN','Term','expires','John','REPORT','IPSWICH','repairs','Water','Total'
  mixed = 'track','sequence','notes','Watson','Miss','with','recording','FAST','LOCATE','erased','TEMPO' }
$log = New-Object System.Collections.Generic.List[object]
function Note($pdf, $kind, $page, $extra) {
  $wins = @(Get-ReaderWindows)
  $dialogs = @($wins | Where-Object { $_ -match '\|#32770\|' })
  $log.Add([pscustomobject]@{ pdf = $pdf; kind = $kind; page = $page; windows = $wins; dialogs = $dialogs; extra = $extra }) }

# one-time UI cleanup: close the All-tools pane and the pin toast, then restart
$m = Open-Reader 'C:\sw\pdf\mixed-default.pdf' 'page=1&view=Fit' -fit
Save-Screen 'setup-after-cleanup'

foreach ($name in $pdfs.Keys) {
  $doc = $pdfs[$name][0]; $n = $pdfs[$name][1]; $pdf = "C:\sw\pdf\$name.pdf"
  "file $name sha256=$((Get-FileHash $pdf).Hash.ToLower())"
  for ($p = 1; $p -le $n; $p++) {
    $tag = '{0}-p{1:d2}' -f $name, $p
    $m = Open-Reader $pdf "page=$p&view=Fit&pagemode=none" -fit
    if (-not $m) { "OPEN FAILED $tag"; Note $name 'fit' $p 'open-failed'; continue }
    Save-Screen "$tag-fit"; Note $name 'fit' $p $m.MainWindowTitle
    $t = Copy-AllText $m
    [IO.File]::WriteAllText("$OutDir\$tag.txt", $t, [Text.UTF8Encoding]::new($false))
    Note $name 'text' $p $t.Length
    $c = $crops.$doc | Where-Object page -eq $p
    $m = Open-Reader $pdf ("page=$p&zoom=400,{0},{1}&pagemode=none" -f $c.left, $c.top)
    Save-Screen "$tag-zoom400"; Note $name 'zoom400' $p ("{0},{1}" -f $c.left, $c.top)
    "done $tag text_len=$($t.Length)"
  }
  foreach ($w in $words[$doc]) {
    $m = Open-Reader $pdf "search=$w" 8
    $sw = Get-ReaderWindows | Where-Object { $_ -match '\|Search$' } | Select-Object -First 1
    if ($sw) { $h = [IntPtr][long]($sw -split '\|')[0]; [W]::ShowWindow($h, 9) | Out-Null; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep 2 }
    Save-Screen ("{0}-search-{1}" -f $name, $w); Note $name 'search' $w ([bool]$sw)
  }
}
Stop-Reader
$log | ConvertTo-Json -Depth 5 | Set-Content "$OutDir\reader-run-log.json" -Encoding UTF8
"dialogs_total=$(@($log | Where-Object { $_.dialogs.Count -gt 0 }).Count)"
