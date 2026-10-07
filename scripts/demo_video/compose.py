"""Compose the Telomy demo video: phone recording + typeset chapter panel + voiceover, 1920×1080 H.264/AAC.

  python scripts/demo_video/compose.py <work_dir>        # expects <work_dir>/clips/<chapter>.mp4
Voice: macOS `say` (Samantha). Fonts: Fraunces + Inter from the mobile app's node_modules.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from script import CARDS, CHAPTERS  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONTS = os.path.join(ROOT, "mobile", "node_modules", "@expo-google-fonts")
BG, INK, MUTED, TEAL, COPPER = (242, 239, 233), (24, 26, 25), (107, 106, 100), (31, 92, 78), (169, 100, 58)
W, H = 1920, 1080
VOICE, RATE = "Samantha", 178


def font(fam, weight, size):
    base = os.path.join(FONTS, fam, weight)
    f = [x for x in os.listdir(base) if x.endswith(".ttf")][0]
    return ImageFont.truetype(os.path.join(base, f), size)


def wrap(d, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur] if cur else lines


def panel(cid, label, title, bullets, card, out):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    if card:
        logo = Image.open(os.path.join(ROOT, "mobile", "assets", "images", "logo-full-ink.png")).convert("RGBA")
        lw = 520 if cid != "engineering" else 300
        logo = logo.resize((lw, int(logo.size[1] * lw / logo.size[0])), Image.LANCZOS)
        y = 250 if cid != "engineering" else 90
        im.paste(logo, ((W - lw) // 2, y), logo)
        y += logo.size[1] + 50
        tf = font("fraunces", "400Regular", 64 if cid != "engineering" else 58)
        for line in wrap(d, title, tf, 1500):
            d.text(((W - d.textlength(line, font=tf)) / 2, y), line, font=tf, fill=INK)
            y += 80
        y += 30
        bf = font("inter", "400Regular", 34)
        for b in bullets:
            d.text(((W - d.textlength(b, font=bf)) / 2, y), b, font=bf, fill=MUTED)
            y += 56
    else:
        x0, y = 860, 300
        d.text((x0, y), label, font=font("inter", "600SemiBold", 26), fill=TEAL)
        y += 60
        tf = font("fraunces", "500Medium", 70)
        for line in wrap(d, title, tf, 960):
            d.text((x0, y), line, font=tf, fill=INK)
            y += 86
        y += 34
        bf = font("inter", "400Regular", 36)
        for b in bullets:
            d.ellipse((x0, y + 17, x0 + 12, y + 29), fill=COPPER)
            for i, line in enumerate(wrap(d, b, bf, 900)):
                d.text((x0 + 34, y), line, font=bf, fill=INK)
                y += 50
            y += 18
        d.text((x0, H - 90), "Telomy · fictitious test data", font=font("inter", "400Regular", 24), fill=MUTED)
        # rounded phone frame shadow
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((270, 50, 270 + 470, 50 + 1000), radius=64, fill=(0, 0, 0, 38))
        im.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(28)))
    im.save(out)


def mask(out):
    m = Image.new("L", (460, 1000), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 459, 999), radius=58, fill=255)
    m.save(out)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", p]).strip())


def main(work):
    os.makedirs(os.path.join(work, "parts"), exist_ok=True)
    mk = os.path.join(work, "mask.png")
    mask(mk)
    parts = []
    for cid, label, title, bullets, narration in CHAPTERS:
        card = cid in CARDS
        png = os.path.join(work, "parts", f"{cid}.png")
        panel(cid, label, title, bullets, card, png)
        aif = os.path.join(work, "parts", f"{cid}.aiff")
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", aif, narration], check=True)
        a = dur(aif)
        T = a + 1.2
        out = os.path.join(work, "parts", f"{cid}.mp4")
        import glob
        pieces = sorted(glob.glob(os.path.join(work, "clips", f"{cid}.mp4")) + glob.glob(os.path.join(work, "clips", f"{cid}_*.mp4")))
        clip = os.path.join(work, "parts", f"{cid}_joined.mp4")
        if len(pieces) == 1:
            clip = pieces[0]
        elif pieces:
            inputs = sum([["-i", x] for x in pieces], [])
            fc = "".join(f"[{i}:v]fps=30,scale=1206:2622,setsar=1[v{i}];" for i in range(len(pieces))) + "".join(f"[v{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=0[v]"
            subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "18", clip],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        audio = ["-i", aif]
        if not card and os.path.exists(clip):
            T = max(T, dur(clip) / 1.5)  # never cut a screen walk short; speed it up at most 1.5×
        if card or not os.path.exists(clip):
            cmd = ["ffmpeg", "-y", "-loop", "1", "-t", f"{T}", "-i", png, *audio,
                   "-filter_complex", f"[0:v]fade=in:st=0:d=0.5,fade=out:st={T - 0.5}:d=0.5,format=yuv420p[v];[1:a]adelay=500|500,apad[a]",
                   "-map", "[v]", "-map", "[a]", "-t", f"{T}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", out]
        else:
            v = dur(clip)
            factor = max(1 / 1.5, min(1.0, T / v))   # long clips get a gentle speed-up (≤1.5×) to fit the narration
            cmd = ["ffmpeg", "-y", "-loop", "1", "-t", f"{T}", "-i", png, "-i", clip, "-i", mk, *audio,
                   "-filter_complex",
                   f"[1:v]setpts=PTS*{factor:.4f},scale=460:1000,tpad=stop_mode=clone:stop_duration={T},trim=duration={T},setpts=PTS-STARTPTS[ph];"
                   f"[2:v]scale=460:1000,format=gray[m];[ph][m]alphamerge[phm];"
                   f"[0:v][phm]overlay=270:50,fade=in:st=0:d=0.4,fade=out:st={T - 0.4}:d=0.4,format=yuv420p[v];[3:a]adelay=500|500,apad[a]",
                   "-map", "[v]", "-map", "[a]", "-t", f"{T}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", out]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        parts.append(out)
        print(f"{cid:12s} {T:5.1f}s")
    lst = os.path.join(work, "parts", "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(ROOT, "share", "telomy-demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", final], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("→", final, f"{dur(final) / 60:.1f} min")


if __name__ == "__main__":
    main(sys.argv[1])
