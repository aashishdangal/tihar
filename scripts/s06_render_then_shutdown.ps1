# Watchdog for the s06 full render (2026-11-16): keeps render_resume.py running until all
# 72 frames are on disk, then shuts the PC down (60 s grace: `shutdown /a` cancels).
$ErrorActionPreference = 'Continue'
$root   = 'E:\Projects\tihar'
$out    = "$root\renders\s06_govardhan"
$blender = 'C:\Users\user\Downloads\blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release\blender.exe'
$log    = "$out\watchdog_log.txt"
function Note($m) { "$(Get-Date -Format HH:mm:ss)  $m" | Tee-Object -FilePath $log -Append }

function FramesDone {
    $n = 0
    for ($f = 1; $f -le 72; $f++) {
        $p = Join-Path $out ('{0:D4}.png' -f $f)
        if ((Test-Path $p) -and (Get-Item $p).Length -gt 10000) { $n++ }
    }
    $n
}
function ResumeRunning {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -like '*render_resume.py*s06_govardhan*' }).Count -gt 0
}

Note 'watchdog started'
$restarts = 0
while ($true) {
    $n = FramesDone
    if ($n -ge 72 -and -not (ResumeRunning)) {
        # owner 2026-11-16: do NOT shut down after the render
        Note "all 72 frames done - watchdog exiting (no shutdown)"
        break
    }
    if (-not (ResumeRunning) -and $n -lt 72) {
        if ($restarts -ge 5) { Note "render_resume gave up 5 times at $n/72 - NOT shutting down"; break }
        $restarts++
        Note "render_resume not running at $n/72 - restart $restarts"
        Start-Process python -WorkingDirectory $root -WindowStyle Minimized -ArgumentList `
            'scripts/render_resume.py', "`"$blender`"", 'blender/scenes/s06_govardhan_v036.blend',
            'scripts/s05_render_frames.py', 'renders/s06_govardhan', '1', '72', '1920', '1080'
        Start-Sleep 60
    }
    Start-Sleep 30
}
