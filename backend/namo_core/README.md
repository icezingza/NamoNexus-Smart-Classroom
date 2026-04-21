# Namo Core Backend

Minimal FastAPI backend rebuilt from the surviving project structure and docs.

## Run

```powershell
cd ..
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r namo_core\requirements.txt
python -m namo_core.main
```

The API exposes:
- `GET /health`
- `GET /status`
- `GET /knowledge/search?q=...`
- `GET /classroom/session`
- `GET /lessons/outline`
- `GET /devices`
- `POST /reasoning/explain`
- `POST /reasoning/chat`

## Test

```powershell
pytest -q
```

## Reasoning Provider

Use mock reasoning by default. To target an OpenAI-compatible endpoint, configure:

```powershell
$env:NAMO_REASONING_PROVIDER="openai-compatible"
$env:NAMO_REASONING_API_BASE_URL="http://localhost:8001/v1"
$env:NAMO_REASONING_API_KEY="your-key"
```

If the provider config is incomplete, or a live provider request fails and
`NAMO_REASONING_ALLOW_MOCK_FALLBACK=true`, the service falls back to the local
mock reasoner so the UI remains usable.
