param(
    [string]$Python = "py -3.12"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "requirements.txt")) {
    throw "Run this script from the NEXUS+ repository root."
}

if (-not (Test-Path "fine_tuned_vit\model.safetensors")) {
    throw "The fine-tuned ViT weights are missing. Clone/pull with Git LFS enabled."
}

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Invoke-Expression "$Python -m venv venv"
}

$venvPython = Join-Path (Get-Location) "venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
if (Test-Path "requirements.lock") {
    & $venvPython -m pip install -r requirements.lock
}

Write-Host "Setup complete. Configure GEMINI_API_KEY and GROQ_API_KEY, then run:"
Write-Host ".\venv\Scripts\Activate.ps1; streamlit run app.py"
