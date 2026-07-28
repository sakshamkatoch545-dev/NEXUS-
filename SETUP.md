# Reproducing NEXUS+

The repository contains the application code, the public dependency list, and
the active `fine_tuned_vit` model artifacts. The local virtual environments and
API credentials are intentionally excluded from GitHub.

## Windows setup

Run PowerShell from the repository root:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If Python 3.12 is not installed, install it from python.org and rerun the
commands. Use the same Python, PyTorch, and model versions as the project for
the closest reproduction.

## API keys

Create your own keys at the Gemini and Groq developer consoles. Then configure
them for the current PowerShell session:

```powershell
$env:GEMINI_API_KEY = "your-own-gemini-key"
$env:GROQ_API_KEY = "your-own-groq-key"
```

Do not paste real keys into source files, commit them, or reuse someone else’s
keys. The API engine uses Gemini first and Groq as fallback; without keys, the
local engines still run but API results are unavailable.

## Run

```powershell
streamlit run app.py
```

For the closest output, use the same input image bytes, model checkpoint,
dependency versions, API provider/model availability, and hardware. API model
responses can change over time, so exact API-backed scores cannot be guaranteed.

## Linux/macOS equivalent

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export GEMINI_API_KEY="your-own-gemini-key"
export GROQ_API_KEY="your-own-groq-key"
streamlit run app.py
```
