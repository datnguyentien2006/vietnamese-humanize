# teacher_chain.ps1 — chạy teacher tuần tự A → B, resume tự động từ cache
$ErrorActionPreference = 'Continue'
$repo = 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
Set-Location $repo
$env:TEACHER_API_BASE = 'http://127.0.0.1:11434/v1'
$env:TEACHER_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
$env:TEACHER_API_KEY = 'local'
$env:TEACHER_TIMEOUT_SECONDS = '300'
$env:TEACHER_EXTRA_JSON = '{"max_tokens": 1024}'

Write-Output "=== WORKER A (docs 1100-2400) $(Get-Date -Format 'HH:mm:ss') ==="
& "$repo\.venv\Scripts\python.exe" training\prepare_dataset.py --mode synthesize --dirtying llm --source training/data/raw_staged_a --out-dir training/data/sft_v2
Write-Output "=== WORKER B (docs 2400-3679) $(Get-Date -Format 'HH:mm:ss') ==="
& "$repo\.venv\Scripts\python.exe" training\prepare_dataset.py --mode synthesize --dirtying llm --source training/data/raw_staged_b --out-dir training/data/sft_v2
Write-Output "=== CHAIN A-B HOAN TAT $(Get-Date -Format 'HH:mm:ss') ==="
