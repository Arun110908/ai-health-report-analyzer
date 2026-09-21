"""
End-to-end OCR test: renders each labelled report to a DEGRADED IMAGE (phone-
photo style: slight rotation, blur, low resolution, JPEG artefacts), runs the
real Tesseract OCR path (app.ocr_extraction.extract_text_from_image) and then
scores the pipeline against ground truth.

    python scripts/evaluate_ocr.py                       # sample_data
    python scripts/evaluate_ocr.py --dir tests_realistic
    python scripts/evaluate_ocr.py --compare             # with vs without preprocessing

Needs the tesseract binary + pytesseract + Pillow.
"""
import argparse
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import app.ocr_extraction as ocr  # noqa: E402

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Courier New.ttf",
    "C:/Windows/Fonts/consola.ttf",
]
FONT = next((c for c in _FONT_CANDIDATES if os.path.exists(c)), None)


QUALITY = "poor"   # "good" = clean 300dpi-ish scan, "poor" = blurry phone photo


def render(text: str, degrade: bool = True) -> bytes:
    font = ImageFont.truetype(FONT, 22) if FONT else ImageFont.load_default()
    lines = text.splitlines()
    w = max(int(font.getlength(l)) for l in lines) + 60
    h = 34 * len(lines) + 60
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        d.text((30, 30 + 34 * i), l, fill=(20, 20, 20), font=font)
    q = 55
    if degrade and QUALITY == "poor":
        img = img.rotate(0.8, expand=True, fillcolor="white")
        img = img.filter(ImageFilter.GaussianBlur(0.9))
        img = img.resize((int(img.width * 0.55), int(img.height * 0.55)), Image.BILINEAR)
    elif degrade:  # good scan: tiny skew, light blur, mild compression
        img = img.rotate(0.3, expand=True, fillcolor="white")
        img = img.filter(ImageFilter.GaussianBlur(0.4))
        q = 85
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q)
    return buf.getvalue()


def run(folder: Path, truth: Path):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in sorted(folder.glob("*.txt")):
            text, _ = ocr.extract_text_from_image(render(f.read_text()))
            (tmp / f.name).write_text(text)
        (tmp / "ground_truth.json").write_text(truth.read_text())
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "evaluate.py"), "--dir", str(tmp)],
                             capture_output=True, text=True).stdout
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "sample_data"))
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--quality", choices=["good", "poor"], default="poor")
    a = ap.parse_args()
    globals()["QUALITY"] = a.quality
    folder = Path(a.dir)
    truth = folder / "ground_truth.json"
    if a.compare:
        keep = (ocr._prep_for_ocr, ocr.OCR_CONFIG)
        ocr._prep_for_ocr, ocr.OCR_CONFIG = (lambda im: im), ""
        print("=== WITHOUT preprocessing ===\n" + "\n".join(run(folder, truth).splitlines()[:6]))
        ocr._prep_for_ocr, ocr.OCR_CONFIG = keep
    print("=== WITH preprocessing ===\n" + "\n".join(run(folder, truth).splitlines()[:16]))
