# restart_teacher_local.ps1 — tiếp tục teacher local sau khi tắt/bật máy
# Chạy: double-click restart_teacher_local.bat (ở cùng thư mục)
$ErrorActionPreference = 'Continue'
$ollama = 'C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe'
$repo = 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'

function Test-Port11434 {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $result = $client.BeginConnect('127.0.0.1', 11434, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne(1500)
        if ($ok -and $client.Connected) { $client.Close(); return $true }
        $client.Close(); return $false
    } catch { return $false }
}

# 1) Bật ollama serve nếu chưa có port 11434
if (-not (Test-Port11434)) {
    Write-Host '[1/2] Bat ollama serve...' -ForegroundColor Cyan
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    $tries = 0
    while (-not (Test-Port11434) -and $tries -lt 15) {
        Start-Sleep -Seconds 2
        $tries++
    }
}
Write-Host '[1/2] Ollama server: OK (port 11434)' -ForegroundColor Green

# 2) Tiep tuc teacher — cache tu resume, khong mat ket qua nao
Write-Host '[2/2] Tiep tuc teacher local (tu dong resume tu cache)...' -ForegroundColor Cyan
Set-Location $repo
$env:TEACHER_API_BASE = 'http://127.0.0.1:11434/v1'
$env:TEACHER_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
$env:TEACHER_API_KEY = 'local'
$env:TEACHER_TIMEOUT_SECONDS = '300'
& "$repo\.venv\Scripts\python.exe" training\prepare_dataset.py --mode synthesize --dirtying llm --source training/data/raw_staged --out-dir training/data/sft_v2
Write-Host ''
Write-Host 'Batch da ket thuc (xong hoac bi giat) — log o cua so nay. Chay lai file nay de tiep tuc.' -ForegroundColor Yellow
