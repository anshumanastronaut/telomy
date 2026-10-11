"""Record the voiceover in your own voice, one frame at a time — a teleprompter in the terminal.

  python scripts/demo_video/record_voice.py <work_dir>                 # all frames, skipping ones already recorded
  python scripts/demo_video/record_voice.py <work_dir> --from twin     # start at a frame
  python scripts/demo_video/record_voice.py <work_dir> --only market   # (re)record one frame
  python scripts/demo_video/record_voice.py --list-mics                # find your microphone's number
  python scripts/demo_video/record_voice.py <work_dir> --mic 1         # use microphone 1 (default 0)

Takes are saved as <work_dir>/voice/<frame>.wav (48 kHz mono). Then run compose.py <work_dir>.
The first run asks macOS for microphone access for your terminal app — allow it.
"""
import argparse
import os
import shutil
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.dirname(__file__))
from script import CHAPTERS  # noqa: E402

B, D, T, C, R = "\033[1m", "\033[2m", "\033[36m", "\033[33m", "\033[0m"


def show(i, n, row):
    cid, label, title, _bullets, vo, direction = row
    width = min(100, shutil.get_terminal_size().columns - 4)
    os.system("clear")
    print(f"{D}frame {i}/{n} · {cid}{R}   {T}{label or 'OPENING'}{R}")
    print(f"{B}{title}{R}\n")
    print(f"{C}Direction:{R} {direction}\n")
    for para in textwrap.wrap(vo, width):
        print(f"  {B}{para}{R}")
    print(f"\n{D}≈ {len(vo.split()) / 2.5:.0f} s at a natural pace{R}")


def record(path, mic):
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "avfoundation", "-i", f":{mic}",
                             "-ac", "1", "-ar", "48000", path], stdin=subprocess.PIPE)
    input(f"\n  🔴 {B}Recording…{R} read the lines, then press Enter to stop. ")
    proc.communicate(b"q")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work", nargs="?")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--only")
    ap.add_argument("--mic", default="0")
    ap.add_argument("--list-mics", action="store_true")
    a = ap.parse_args()
    if a.list_mics:
        out = subprocess.run(["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""], capture_output=True, text=True).stderr
        print("\n".join(line.split("] ", 1)[-1] for line in out.splitlines() if "audio devices" in line or ("[" in line and "] [" in line and "AVFoundation" in line and "video" not in line.lower())))
        return
    if not a.work:
        ap.error("give the work directory (the folder that holds clips/)")
    vdir = os.path.join(a.work, "voice")
    os.makedirs(vdir, exist_ok=True)
    rows = list(CHAPTERS)
    if a.only:
        rows = [r for r in rows if r[0] == a.only]
    elif a.start:
        ids = [r[0] for r in rows]
        rows = rows[ids.index(a.start):]
    n = len(CHAPTERS)
    for row in rows:
        i = [r[0] for r in CHAPTERS].index(row[0]) + 1
        path = os.path.join(vdir, f"{row[0]}.wav")
        if os.path.exists(path) and not a.only and not a.start:
            continue
        while True:
            show(i, n, row)
            k = input(f"\n  Enter = record · s = skip · q = quit  ").strip().lower()
            if k == "q":
                return
            if k == "s":
                break
            record(path, a.mic)
            subprocess.run(["afplay", path])
            k = input(f"\n  {B}k{R} = keep · {B}r{R} = redo · {B}q{R} = keep and quit  ").strip().lower()
            if k == "r":
                continue
            if k == "q":
                return
            break
    done = sum(os.path.exists(os.path.join(vdir, f"{r[0]}.wav")) for r in CHAPTERS)
    print(f"\n{done}/{n} frames recorded. Next: python scripts/demo_video/compose.py {a.work}")


if __name__ == "__main__":
    main()
