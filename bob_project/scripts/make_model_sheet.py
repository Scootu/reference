"""Assemble design/bob_model_sheet.png from the test renders (plain Python + Pillow).

    python scripts/make_model_sheet.py        (run from bob_project/, after render_tests.py)
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "renders")
OUT = os.path.join(ROOT, "design")

PALETTE = [("skin", "#F6F7F0"), ("skin shade", "#E7E4DE"), ("ink", "#2A2324"),
           ("stroke", "#3A3436"), ("hair", "#1E203C"), ("robe", "#264080"),
           ("robe rim", "#4E6493"), ("skirt", "#22397A"), ("sash", "#DCA54B"),
           ("gold trim", "#EDBD4D"), ("tear", "#8CCCFF")]


def font(size):
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def fit(im, w, h):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    W = 2400
    bg = (30, 32, 38)
    sheet = Image.new("RGB", (W, 2900), bg)
    d = ImageDraw.Draw(sheet)
    d.text((40, 30), "BOB — model sheet", fill=(240, 240, 245), font=font(64))
    d.text((40, 110), "2.5D flat character in a glowing 3D world · deadpan court clerk of the "
           "Kingdom of Lumen · see BOB_DESIGN.md", fill=(180, 182, 190), font=font(28))

    # row 1: full body front + 3/4, portraits front / 3/4 / side / back
    y = 170
    x = 40
    for name, w in (("05_fullbody_front", 420), ("06_fullbody_three_quarter", 420)):
        p = os.path.join(R, "portraits", f"{name}.png")
        if os.path.exists(p):
            im = fit(Image.open(p), w, 630)
            sheet.paste(im, (x, y))
            x += im.width + 20
    for name in ("01_front_portrait", "02_three_quarter_portrait", "03_side_profile",
                 "04_back_view"):
        p = os.path.join(R, "portraits", f"{name}.png")
        if os.path.exists(p):
            im = fit(Image.open(p), 360, 360)
            col = (x if name in ("01_front_portrait", "03_side_profile") else x + 380)
            row = y if name in ("01_front_portrait", "02_three_quarter_portrait") else y + 380
            sheet.paste(im, (col, row))
    d.text((40, y + 650), "Turnaround: front · 3/4 · profile · back", fill=(200, 200, 210),
           font=font(30))

    # row 2: expression sheet
    y = 880
    p = os.path.join(R, "expressions", "bob_expression_sheet.png")
    if os.path.exists(p):
        im = fit(Image.open(p), W - 80, 1500)
        sheet.paste(im, (40, y))
        y += im.height + 30

    # row 3: palette
    d.text((40, y), "Palette (sRGB)", fill=(240, 240, 245), font=font(36))
    y += 60
    sw = (W - 80) // len(PALETTE)
    for i, (n, hx) in enumerate(PALETTE):
        x0 = 40 + i * sw
        d.rectangle((x0, y, x0 + sw - 12, y + 120), fill=hx, outline=(90, 90, 100))
        d.text((x0, y + 130), n, fill=(220, 220, 228), font=font(24))
        d.text((x0, y + 160), hx, fill=(160, 162, 170), font=font(22))
    y += 220
    sheet = sheet.crop((0, 0, W, y))
    out = os.path.join(OUT, "bob_model_sheet.png")
    sheet.save(out)
    print("[bob] model sheet ->", out)


if __name__ == "__main__":
    main()
