# Helpers for driving Adobe Reader in the interactive session.
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(150); mouse_event(2,0,0,0,IntPtr.Zero); mouse_event(4,0,0,0,IntPtr.Zero); }
  public static List<string> Windows(HashSet<uint> pids) {
    var r = new List<string>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p);
      if (pids.Contains(p) && IsWindowVisible(h)) { var t = new StringBuilder(512); var c = new StringBuilder(256);
        GetWindowText(h, t, 512); GetClassName(h, c, 256); r.Add(h.ToInt64() + "|" + p + "|" + c + "|" + t); }
      return true; }, IntPtr.Zero);
    return r; }
}
"@
[W]::SetProcessDPIAware() | Out-Null
$global:Acro = 'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe'
$global:OutDir = '\\10.0.2.4\qemu\out\reader'
New-Item -ItemType Directory -Force $OutDir | Out-Null

function Stop-Reader { Get-Process Acrobat, AcroCEF, RdrCEF, AdobeCollabSync -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2 }
function Get-ReaderWindows {
  $pids = [System.Collections.Generic.HashSet[uint32]]::new()
  Get-Process Acrobat, AcroCEF -ErrorAction SilentlyContinue | ForEach-Object { [void]$pids.Add([uint32]$_.Id) }
  [W]::Windows($pids) }
function Open-Reader($pdf, $params, $settle = 6, [switch]$fit) {
  Stop-Reader
  $args = if ($params) { "/A `"$params`" `"$pdf`"" } else { "`"$pdf`"" }
  Start-Process $Acro -ArgumentList $args | Out-Null
  $name = [IO.Path]::GetFileName($pdf); $deadline = (Get-Date).AddSeconds(60); $main = $null
  while ((Get-Date) -lt $deadline -and -not $main) {
    Start-Sleep 1
    $main = Get-Process Acrobat -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*$name*" } | Select-Object -First 1 }
  if (-not $main) { return $null }
  [W]::ShowWindow($main.MainWindowHandle, 3) | Out-Null   # maximize
  [W]::SetForegroundWindow($main.MainWindowHandle) | Out-Null
  Start-Sleep 2
  Close-Clutter
  if ($fit) { [W]::Click(1700, 900); Start-Sleep 1; [System.Windows.Forms.SendKeys]::SendWait('^0') }
  Start-Sleep $settle
  return $main }
function Close-Clutter {
  # All-tools pane close button and the Windows 'pin to taskbar' toast, if present
  [W]::Click(260, 108); Start-Sleep 1
  [W]::Click(1806, 1346); Start-Sleep 1 }
function Save-Screen($name) {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save("$OutDir\$name.png", [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose() }
function Copy-AllText($main) {
  [W]::SetForegroundWindow($main.MainWindowHandle) | Out-Null
  Set-Clipboard -Value 'SW_EMPTY'
  [W]::Click(1700, 900); Start-Sleep 1
  [System.Windows.Forms.SendKeys]::SendWait('^a'); Start-Sleep 2
  [System.Windows.Forms.SendKeys]::SendWait('^c'); Start-Sleep 3
  Get-Clipboard -Raw }
