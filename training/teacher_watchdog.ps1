# teacher_watchdog.ps1 — tự chữa: đảm bảo CẢ A và B đều có worker; stall 10 phút → kill + relaunch
$repo = 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
$cache = "$repo\training\data\sft\teacher_cache.jsonl"
$log = "$repo\training\data\teacher_watchdog.log"
$halfA = "$repo\training\run_half_a.ps1"
$halfB = "$repo\training\run_half_b.ps1"

function Get-CacheLines { if (Test-Path $cache) { (Get-Content $cache | Measure-Object -Line).Lines } else { 0 } }
function Get-PidsFor([string]$source) {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match $source } | ForEach-Object { $_.ProcessId })
}
function Start-Half([string]$script) {
    Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WindowStyle Hidden
}

Add-Content $log "=== watchdog v3 start $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
$stall = 0
$last = Get-CacheLines

while ($true) {
    Start-Sleep -Seconds 300
    $now = Get-CacheLines
    $pa = @(Get-PidsFor 'raw_staged_a'); $pb = @(Get-PidsFor 'raw_staged_b')
    Add-Content $log ("[{0}] cache={1} (+{2}) workers A={3} B={4}" -f (Get-Date -Format 'HH:mm:ss'), $now, ($now - $last), $pa.Count, $pb.Count)

    if ($now -ge 7000) {
        Add-Content $log "[watchdog] cache đạt $now >= 7000 (coverage mục tiêu ~7.500) -> watchdog dừng"
        break
    }

    if ($now -le $last) { $stall++ } else { $stall = 0 }
    $last = $now

    if ($stall -ge 2) {
        Add-Content $log "[watchdog] STALL 10 phút -> kill toàn bộ + relaunch A+B"
        foreach ($p in ($pa + $pb)) { taskkill /T /F /PID $p 2>&1 | Out-Null }
        Start-Sleep -Seconds 5
        Start-Half $halfA
        Start-Half $halfB
        $stall = 0
        continue
    }
    if ($pa.Count -eq 0) { Add-Content $log "[watchdog] A chết -> relaunch A"; Start-Half $halfA }
    if ($pb.Count -eq 0) { Add-Content $log "[watchdog] B chết -> relaunch B"; Start-Half $halfB }
}
