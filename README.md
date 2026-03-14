Voice-to-Resume - Whisper Integration

This project collects voice inputs to populate a resume template and now supports improved speech-to-text using OpenAI's Whisper model.

How it works:
- The front-end (`templates/index.html`) records audio via the browser's MediaRecorder and posts the audio blob to the Flask backend.
- The Flask backend (`app.py`) forwards the audio to OpenAI's Whisper transcription API (`v1/audio/transcriptions`), receives the text, sanitizes/parses it, and returns structured parsed fields.
- The front-end populates the preview based on the returned parsed values.

Setup & Run:
1. Install using Miniconda (recommended):

Windows Miniconda Prompt (cmd.exe-like):

```powershell
conda create -n voice-resume python=3.11 -y
conda activate voice-resume
pip install -r requirements.txt
```

If you prefer a Python venv (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate
pip install -r requirements.txt
```

2. Set your OpenAI API key in the environment (choose one):

Temporary for current PowerShell session:

```powershell
$Env:OPENAI_API_KEY = "sk-..."
```

Temporary for current Miniconda Prompt (cmd):

```bat
set OPENAI_API_KEY=sk-...
```

Persistent (available in new shells):

```powershell
setx OPENAI_API_KEY "sk-..."
```

Or: store in a file so you don't need to set it every session. Supported files: `.openai_key`, `openai_key.txt`, or `.env` (first non-empty line or `OPENAI_API_KEY=` entry).

Windows (Miniconda prompt / cmd):

```bat
echo sk-... > .openai_key
```

PowerShell (current folder):

```powershell
Set-Content -Path .openai_key -Value "sk-..." -NoNewline
```

Make sure to add `.openai_key` to `.gitignore` to avoid committing it to your repo.

If you store the key in `.env`, `app.py` will load it automatically (we use python-dotenv). Example `.env` contents:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

Install `python-dotenv` (if you didn't) and restart the server or re-open the terminal for the key to be picked up by `load_dotenv()`:

```powershell
pip install python-dotenv
```

Short steps to get an OpenAI API key (very short):
1. Go to https://platform.openai.com and sign up / sign in.
2. Open the API Keys page (Account → View API Keys) and click "Create new secret key".
3. Copy the key and store it securely (you won't be able to view it again).
4. Set the key locally (see step above) and keep it private.

3. Run the app:

```powershell
python app.py
```

4. Open the app at `http://127.0.0.1:5000` and use the `Record (Whisper)` button to record and transcribe using Whisper.

If you prefer the official OpenAI library instead of raw requests, install:

```powershell
pip install openai
```

Notes:
- If you don't want to use Whisper (for privacy or offline testing), the original SpeechRecognition flow still works.
- Keep your API key secret; don't push it into source control.
- You may need to increase the server timeout depending on the audio length.
