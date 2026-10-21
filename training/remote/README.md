# Getting the GPU training started

The whole pipeline runs from one generated file: [`humanizer_colab.ipynb`](humanizer_colab.ipynb)
(clone → install → corpus → prepare dataset → train → merge/AWQ export).
Three ways to execute it, in order of practicality:

## Route A — Google Colab, notebook in the UI (recommended first run)

1. Open [colab.research.google.com](https://colab.research.google.com/), sign in, then
   `File → Upload notebook` and select `training/remote/humanizer_colab.ipynb`.
2. `Runtime → Change runtime type → GPU (T4)` and confirm.
3. Edit the CONFIG cell (Drive paths for DATA_RAW / PERSIST_DIR) and run all cells
   (Ctrl+F9).
4. Training takes a few hours on a T4; keep the tab open or run a queue on
   `Runtime → View resources`. Artifacts land in the Drive folder you set in
   PERSIST_DIR (set it — otherwise the adapter lives only in the session).

Limitation: a T4 is fine, but the 14B run occupies the GPU continuously; if you
get `CUDA out of memory`, cell 4 automatically re-runs `Qwen/Qwen2.5-7B-Instruct`.

## Route B — Kaggle Notebooks API, automated from the command line

This is the closest thing to a "Colab CLI" — a real, official CLI that submits
training to a free GPU without any browser. Free quota is 30 GPU-hours/week.

1. Create a Kaggle account + get a token: kaggle.com → Settings →
   API → **Create New Token** → place the downloaded `kaggle.json` at
   `%USERPROFILE%\.kaggle\kaggle.json` (Windows) or `~/.kaggle/kaggle.json`.
2. Upload the corpus as a **private Kaggle dataset**: kaggle.com/Datasets →
   New Dataset → upload your human-written text files.
3. Fill in `kernel-metadata.json`:
   - `id`: `YOUR_KAGGLE_USERNAME/humanizer-vi-train`
   - `dataset_sources`: `["YOUR_KAGGLE_USERNAME/corpus-name"]`
4. Push and watch it run:
   ```powershell
   pip install kaggle
   training/remote> kaggle kernels push
   training/remote> kaggle kernels status  YOUR_USERNAME/humanizer-vi-train
   training/remote> kaggle kernels output YOUR_USERNAME/humanizer-vi-train
   ```

Useful for unattended runs: Kaggle keeps the notebook output (LoRA adapter) as a
downloadable artifact when the run finishes. Internet access is enabled in the
metadata for cloning the repo and pulling the base model; add
`OS="GIT repo token"` if the repo is private (or push a fork).

## Route C — I drive your local Chrome to set Colab up

Possible, but with hard limits: I can visualize and fill cells, click
"Connect GPU", and run the setup cells, but not babysit a multi-hour training
job (session timeouts, OAuth/Drive prompts require your interaction, and the
free tier enforces inactivity disconnects on long jobs).

If you want this anyway: be signed into Google in the automated browser, tell
me where the corpus files sit (Drive path or local folder), and I will open
colab.research.google.com, fill in the notebook, and click "Run all" — you only
confirm the Drive/GPU dialogs.

## Minimum before any route works

- The **corpus exists somewhere reachable**: local folder, Drive, or Kaggle
  dataset (`.txt` / `.txt.gz` / `.jsonl` / `.parquet`, see
  [`../README.md`](../README.md) for shape + license rules).
- If the repo goes private first, adjust the clone step (deploy token for
  GitHub, or upload the repo as a Kaggle dataset).
