# run_half_a.ps1 — worker A: docs 1100-2400 (resume tự động từ cache)
$repo = 'C:\Tools HumanizeAI\vietnamese-humanizev1.3\vietnamese-humanizer'
Set-Location $repo
$env:TEACHER_API_BASE = 'http://127.0.0.1:11434/v1'
$env:TEACHER_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
$env:TEACHER_API_KEY = 'local'
$env:TEACHER_TIMEOUT_SECONDS = '300'
$env:TEACHER_EXTRA_JSON = '{"max_tokens": 1024}'
& "$repo\.venv\Scripts\python.exe" training\prepare_dataset.py --mode synthesize --dirtying llm --source training/data/raw_staged_a --out-dir training/data/sft_v2
