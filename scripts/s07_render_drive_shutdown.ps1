# Watchdog for the s07 full render (owner 2026-11-17): keeps render_resume.py running until all
# 272 frames are on disk, copies them to Google Drive (G:\My Drive\renders\s07_bhaitika), waits
# for Drive for desktop to finish uploading, then shuts the PC down (120 s grace: `shutdown /a`
# cancels). If the render gives up, it does NOT copy or shut down.
$ErrorActionPreference = 'Continue'
$root    = 'E:\Projects\tihar'
$scene   = 's07_bhaitika'
$blend   = 'blender/scenes/s07_bhaitika_v041.blend'
$last    = 272
$out     = "$root\renders\$scene"
$drive   = "G:\My Drive\renders\$scene"
$blender = 'C:\Users\user\Downloads\blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release\blender.exe'
$log     = "$out\watchdog_log.txt"
New-Item -ItemType Directory -Force $out | Out-Null
function Note($m) { "$(Get-Date -Format 'MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $log -Append }

function FramesDone {
    $n = 0
    for ($f = 1; $f -le $last; $f++) {
        $p = Join-Path $out ('{0:D4}.png' -f $f)
        if ((Test-Path $p) -and (Get-Item $p).Length -gt 10000) { $n++ }
    }
    $n
}
function ResumeRunning {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -like "*render_resume.py*$scene*" }).Count -gt 0
}
function DriveIO {
    # bytes moved by Google Drive for desktop (network upload counts as "other"/read I/O)
    $s = 0
    Get-CimInstance Win32_Process -Filter "Name='GoogleDriveFS.exe'" | ForEach-Object {
        $s += [double]$_.ReadTransferCount + [double]$_.OtherTransferCount + [double]$_.WriteTransferCount }
    $s
}

$env:RENDER_STALL_S = '900'   # s07 is built on s02: long single-threaded first object sync
Note 'watchdog started'
$restarts = 0
$ok = $false
while ($true) {
    $n = FramesDone
    if ($n -ge $last -and -not (ResumeRunning)) { Note "all $last frames done"; $ok = $true; break }
    if (-not (ResumeRunning) -and $n -lt $last) {
        if ($restarts -ge 5) { Note "render_resume gave up 5 times at $n/$last - NOT copying, NOT shutting down"; break }
        $restarts++
        Note "render_resume not running at $n/$last - start $restarts"
        Start-Process python -WorkingDirectory $root -WindowStyle Minimized -ArgumentList `
            'scripts/render_resume.py', "`"$blender`"", $blend,
            'scripts/s05_render_frames.py', "renders/$scene", '1', "$last", '1920', '1080'
        Start-Sleep 60
    }
    Start-Sleep 30
}
if (-not $ok) { exit 1 }

# ---- copy to Google Drive ----
New-Item -ItemType Directory -Force $drive | Out-Null
Note "copying frames to $drive"
robocopy $out $drive '*.png' /NFL /NDL /NJH /R:3 /W:10 | Out-Null
$copied = @(Get-ChildItem $drive -Filter '????.png').Count
Note "copied: $copied png in Drive folder"
if ($copied -lt $last) { Note "copy incomplete ($copied/$last) - NOT shutting down"; exit 1 }

# ---- wait for Drive upload: min 10 min, then until Drive I/O is quiet for 6 min (max 120 min) ----
Start-Sleep 600
$quiet = 0; $prev = DriveIO
for ($i = 0; $i -lt 55 -and $quiet -lt 3; $i++) {
    Start-Sleep 120
    $now = DriveIO
    $mb = [math]::Round(($now - $prev) / 1MB, 1)
    if ($mb -lt 2) { $quiet++ } else { $quiet = 0 }
    Note "Drive I/O last 2 min: $mb MB (quiet $quiet/3)"
    $prev = $now
}
Note 'shutting down in 120 s (run: shutdown /a to cancel)'
shutdown /s /t 120 /c "s07 render done and copied to Google Drive - shutting down"
