# Intel Assistant

Intel is a local Windows voice assistant built around:

- custom wake word detection via `openWakeWord`
- speech-to-text via `faster-whisper`
- local tool selection via `Ollama` + `gemma3`
- desktop automation tools for files, apps, browser tabs, and YouTube Music
- local TTS via Windows SAPI voices

This repository now supports a portable Windows build using `PyInstaller`.

## What the app does

Runtime flow:

1. `Intel.exe` starts in continuous wake word mode.
2. You say `Intel`.
3. The assistant records the command.
4. `faster-whisper` transcribes the audio.
5. `gemma3` decides whether to answer directly or call a local tool.
6. Intel prints and speaks the response.

## Repository layout

- [app/main.py](/d:/Desktop/Development/AI-Assistant/app/main.py) - main runtime entrypoint
- [app/core/assistant_service.py](/d:/Desktop/Development/AI-Assistant/app/core/assistant_service.py) - dialogue/tool orchestration
- [app/llm/tool_selector.py](/d:/Desktop/Development/AI-Assistant/app/llm/tool_selector.py) - tool vs chat decision layer
- [app/tools](/d:/Desktop/Development/AI-Assistant/app/tools) - file/app/browser tools
- [app/voice](/d:/Desktop/Development/AI-Assistant/app/voice) - wake word, STT, TTS, sound cues
- [data/wakeword/models](/d:/Desktop/Development/AI-Assistant/data/wakeword/models) - trained wake word models
- [data/sounds](/d:/Desktop/Development/AI-Assistant/data/sounds) - start/end voice command cues
- [utils/wakeword](/d:/Desktop/Development/AI-Assistant/utils/wakeword) - dataset and training utilities
- [scripts/build_portable.py](/d:/Desktop/Development/AI-Assistant/scripts/build_portable.py) - portable build script for `py`
- [scripts/build_portable.ps1](/d:/Desktop/Development/AI-Assistant/scripts/build_portable.ps1) - portable build script
- installs tray app into Windows Startup
- [Intel.spec](/d:/Desktop/Development/AI-Assistant/Intel.spec) - PyInstaller spec

## Prerequisites for development

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Optional build dependency:

```powershell
python -m pip install -r requirements-build.txt
```

Optional wakeword training dependencies:

```powershell
python -m pip install -r requirements-train.txt
```

Optional `.tflite` export dependencies:

```powershell
python -m pip install -r requirements-tflite.txt
```

## Environment configuration

Create `.env` in the project root. A ready template is available at [.env.example](/d:/Desktop/Development/AI-Assistant/.env.example).

Important runtime variables:

```env
INTEL_WAKEWORD_PHRASE="Intel"
INTEL_WAKEWORD_MODEL_KEY="intel"
INTEL_WAKEWORD_MODEL_PATH="data/wakeword/models/intel.onnx"

INTEL_COMMAND_START_CUE_PATH="data/sounds/intel_start.wav"
INTEL_COMMAND_END_CUE_PATH="data/sounds/intel_end.wav"

INTEL_STT_MODEL_SIZE=small
# Optional fully local STT model folder:
# INTEL_STT_MODEL_PATH="models/faster-whisper/small"

INTEL_TTS_RU_VOICE_NAME="Seva"
INTEL_TTS_EN_VOICE_NAME="David"
```

Paths in `.env` can now be relative to the app root. This is important for portable builds.

## Running from source

```powershell
python app\main.py
```

## Portable build

The project is packaged as a one-folder Windows application. This is the recommended format because:

- audio and model assets stay readable next to the executable
- `.env` remains editable after build
- large binary dependencies behave more reliably than in one-file mode
- runtime installation does not need training or TensorFlow export packages

### Build command

From the repository root:

```powershell
py .\scripts\build_portable.py --clean
```

or:

```powershell
.\scripts\build_portable.ps1 -Clean
```

This script will:

1. install `PyInstaller`
2. build the app with [Intel.spec](/d:/Desktop/Development/AI-Assistant/Intel.spec)
3. create `dist\Intel`
4. copy runtime assets into `dist\Intel\data`, including sounds and wake word models
5. copy `.env.example` into `dist\Intel\.env` if it does not already exist
6. create `data\input` and `logs` directories in the portable output

### Portable output

After a successful build, the portable folder will be:

```text
dist\Intel\
  Intel.exe
  IntelTray.exe
  .env
  README.md
  data\
    sounds\
    wakeword\
      models\
    input\
```

You can move the entire `dist\Intel` folder to another Windows machine.

## Installing on another PC

### Minimum steps

1. Copy `dist\Intel` to the target machine.
2. Open `dist\Intel\.env` and verify paths.
3. Ensure the required external components below are installed.
4. Run:

```powershell
.\IntelTray.exe
```

Use `Intel.exe` when you want a console window for debugging.
Use `IntelTray.exe` when you want Intel to work in the background from the system tray.

## What is included in the build

Packed into the portable app:

- your Python runtime
- Intel application code
- `Intel.exe` for console/debug launches
- `IntelTray.exe` for background tray launches
- local tool implementations
- sound cues from `data/sounds`
- the wake word model from `data/wakeword/models`
- `openWakeWord` runtime resources collected by PyInstaller

## What is NOT automatically embedded and must be installed or provided manually

These are the important external components that are not safely or cleanly embedded into `Intel.exe`:

### 1. Ollama

Required for LLM reasoning and tool selection.

Install manually on the target machine:

- https://ollama.com/download/

### 2. Ollama model

Your app currently expects `gemma3` in Ollama.

Install manually:

```powershell
ollama pull gemma3
```

### 3. `faster-whisper` model weights

These are not automatically bundled by default.

You have two options:

1. Let Intel download them on first run.
2. Copy a local model folder manually and point `.env` to it:

```env
INTEL_STT_MODEL_PATH="models/faster-whisper/small"
```

Recommended for a true portable offline setup:

- pre-download the model on your machine
- copy it into `dist\Intel\models\faster-whisper\small`
- set `INTEL_STT_MODEL_PATH` accordingly

### 4. Windows SAPI voices

Your current TTS setup depends on Windows-installed SAPI voices.

These cannot be reliably embedded into the application folder.

Important voices in your current setup:

- `Seva` for Russian
- `David` for English

On a different machine, you may need to install `Seva` manually and update `.env` if the voice name differs.

### 5. Target desktop applications

Intel can open and control apps like:

- Google Chrome
- Telegram
- Steam
- Visual Studio Code

These applications are not part of the Intel build. They must already be installed on the target PC if you expect Intel to launch them.

### 6. Microphone access and Windows audio environment

Not bundled:

- microphone permissions
- audio drivers
- Windows privacy settings

The target machine must allow microphone access for desktop apps.

### 7. Optional GPU/CUDA stack

If you later switch STT or other components to GPU mode, CUDA drivers are also external and must be installed separately.

## Recommended portable strategy

For the smoothest transfer to another machine:

1. Build in CPU mode.
2. Keep all Intel-owned assets inside the portable folder.
3. Use relative paths in `.env`.
4. Copy your wake word model into `data/wakeword/models`.
5. Optionally copy the local `faster-whisper` model into `models/faster-whisper`.
6. Install `Ollama` and `gemma3` manually on the destination machine.
7. Install the `Seva` SAPI voice manually if you want the same Russian TTS voice.

## Example portable `.env`

```env
INTEL_WAKEWORD_PHRASE="Intel"
INTEL_WAKEWORD_MODEL_KEY="intel"
INTEL_WAKEWORD_MODEL_PATH="data/wakeword/models/intel.onnx"

INTEL_COMMAND_START_CUE_PATH="data/sounds/intel_start.wav"
INTEL_COMMAND_END_CUE_PATH="data/sounds/intel_end.wav"

INTEL_WAKEWORD_THRESHOLD=0.60
INTEL_WAKEWORD_MIN_RMS=220
INTEL_WAKEWORD_MIN_CONSECUTIVE_HITS=2
INTEL_WAKEWORD_COOLDOWN_SEC=3.0
INTEL_WAKEWORD_IDLE_RESET_SEC=4.0
INTEL_WAKEWORD_INSTANT_THRESHOLD=0.72
INTEL_WAKEWORD_WINDOW_FRAMES=4
INTEL_WAKEWORD_WINDOW_RATIO=0.82
INTEL_WAKEWORD_PRE_ROLL_CHUNKS=8

INTEL_WAKEWORD_DEBUG=0
INTEL_WAKEWORD_DEBUG_SCORE_THRESHOLD=0.10
INTEL_REQUIRE_WAKEWORD_IN_TRANSCRIPT=0

INTEL_COMMAND_START_TIMEOUT_SEC=7.0
INTEL_COMMAND_MAX_DURATION_SEC=12.0
INTEL_COMMAND_SILENCE_DURATION_SEC=1.3

INTEL_STT_MODEL_SIZE=small
INTEL_STT_MODEL_PATH="models/faster-whisper/small"
INTEL_STT_DEVICE=cpu
INTEL_STT_COMPUTE_TYPE=int8
INTEL_STT_BEAM_SIZE=5
INTEL_STT_BEST_OF=3
INTEL_STT_TEMPERATURE=0.0
INTEL_STT_VAD_MIN_SILENCE_MS=500

INTEL_TTS_ENABLED=1
INTEL_TTS_RU_VOICE_NAME="Seva"
INTEL_TTS_EN_VOICE_NAME="David"
INTEL_TTS_RATE=2
INTEL_TTS_VOLUME=100
INTEL_TTS_MAX_CHARS=280
```

## Notes about portability limits

Intel can be made portable as an application folder, but it is not a fully self-contained universal appliance yet because:

- Ollama remains an external service
- LLM weights remain external to the executable
- SAPI voices are Windows-level components
- desktop apps Intel controls belong to the host machine

So the best practical definition of "portable" here is:

- one transferable Intel folder
- plus a short manual install checklist on the target PC

## Future improvements

Potential next steps for even better portability:

- add a first-run dependency checker screen
- add a local STT model downloader into the app
- add an installer that checks Ollama, voices, and microphone access
- add a zip export command for the full portable folder
- replace SAPI TTS with a fully local bundled voice engine

## Run Intel in the background on Windows startup

The recommended background mode is `IntelTray.exe`.

It starts Intel in the system tray and provides:

- `Start`
- `Stop`
- `Open Folder`
- `Exit`

### Install tray auto-start

After building the app:

This creates a startup command file in the current user's Windows Startup folder and points it to:

```text
dist\Intel\IntelTray.exe
```