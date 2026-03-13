# Wakeword Dataset Prep

Use this folder to collect and normalize audio for a custom wakeword model for the phrase `Intel`.

## Where to put raw files

Place your raw WAV clips here:

- `data/wakeword/raw/intel_positive/`
  - clips that contain only the wakeword `Intel`
- `data/wakeword/raw/intel_negative/`
  - clips with normal speech that do not contain the word `Intel`

You can either copy WAV files there manually or record them with `record_dataset.py`.

## Recommended MVP dataset size

- `intel_positive`: at least 60 clips
- `intel_negative`: at least 120 clips

Better quality for a first real test:

- `intel_positive`: 150 to 300 clips
- `intel_negative`: 300 to 600 clips

## Recording suggestions

- Record in the same room and with the same microphone you plan to use later.
- Say `Intel` with different speed, loudness, and distance to the mic.
- Add some clips with light room noise.
- Negative clips should contain random phrases, but never the word `Intel`.

## Commands

Record positive samples:

```powershell
.\.venv\Scripts\python.exe utils\wakeword\record_dataset.py --label positive --count 50
```

Record negative samples:

```powershell
.\.venv\Scripts\python.exe utils\wakeword\record_dataset.py --label negative --count 100
```

Normalize and split the dataset:

```powershell
.\.venv\Scripts\python.exe utils\wakeword\prepare_dataset.py --trim-silence
```

Prepared files will be written to:

- `data/wakeword/prepared/positive_train/`
- `data/wakeword/prepared/positive_val/`
- `data/wakeword/prepared/negative_train/`
- `data/wakeword/prepared/negative_val/`

## Important limitation

This repo now includes dataset collection and normalization only.

Training a true custom `Intel` wakeword model for `openWakeWord` still requires a separate training pipeline with extra dependencies such as `torch`, `torchinfo`, and `torchmetrics`, plus the full `openWakeWord` training configuration.
