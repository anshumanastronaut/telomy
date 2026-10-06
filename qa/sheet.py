import glob, os, sys
from PIL import Image, ImageDraw
files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "shots", "*.png")))
W, H, cols = 300, 652, 6
for k in range(0, len(files), 12):
    chunk = files[k:k+12]
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, (H + 22) * rows), "white")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(chunk):
        im = Image.open(f).convert("RGB").resize((W, H))
        x, y = (i % cols) * W, (i // cols) * (H + 22)
        sheet.paste(im, (x, y + 22))
        d.text((x + 4, y + 4), os.path.basename(f)[:-4][:40], fill="black")
    out = os.path.join(os.path.dirname(__file__), f"sheet_{k//12+1}.jpg")
    sheet.save(out, quality=70)
    print(out)
