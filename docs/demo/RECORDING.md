# Recording the demo voiceover

The demo video (`share/telomy-demo.mp4`) is built from three things:

| Input | Where | Made by |
|---|---|---|
| Screen clips | `share/demo/clips/<frame>.mp4` (or `<frame>_1.mp4`, `_2` …) | `scripts/demo_video/rec.sh start <frame>` / `stop` while driving the iOS Simulator |
| Voiceover | `share/demo/voice/<frame>.wav` | `scripts/demo_video/record_voice.py` (your voice) — frames without a take use a macOS `say` scratch voice |
| Script | `scripts/demo_video/script.py` | frame id, panel label/title/bullets, voiceover line, delivery direction |

`share/` is git-ignored: clips and recordings stay on the machine that made them.

## Record

```bash
cd ~/telomy-app
.venv-tools/bin/python scripts/demo_video/record_voice.py --list-mics      # optional: find your mic's number
.venv-tools/bin/python scripts/demo_video/record_voice.py share/demo       # add --mic N if not the default
```

For each frame it shows the line and the delivery note, records until you press Enter, plays the take back, and asks keep / redo.
Already-recorded frames are skipped; `--only <frame>` re-records one, `--from <frame>` resumes.
The first run asks macOS for microphone access for your terminal app.

Tips: a quiet room with soft furnishings, the mic a hand's width away, one frame per take, and read as if explaining to one person.

## Build

```bash
.venv-tools/bin/python scripts/demo_video/compose.py share/demo
```

Each take is trimmed of leading/trailing silence, low-cut at 80 Hz and normalised to −16 LUFS. Each frame lasts as long as its
voiceover (screen clips are sped up at most 1.5× and never cut short). The run prints which frames used your voice.

Before an investor send, fill `ASK` and `USE_OF_FUNDS` at the top of `script.py`, and add real traction only once it exists.
