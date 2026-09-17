"""Generate branded QR codes (sloth center mark) for site URLs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import qrcode
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = REPO_ROOT / "assets" / "images"

DARK = (45, 49, 66)
BG = (255, 255, 255)

PRESETS: dict[str, dict[str, str]] = {
    "website": {
        "url": "https://modafarshouha.github.io/modafarshouha/",
        "out": str(IMAGES_DIR / "website-qr.png"),
        "center": "sloth",
    },
    "blog": {
        "url": "https://modafarshouha.github.io/sloth-blog/blog/",
        "out": str(IMAGES_DIR / "blog-qr.png"),
        "center": "sloth_glasses",
    },
}


def label_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or ""
    path = parsed.path.strip("/")
    return f"{host}/{path}" if path else host


def load_font(size: int, emoji: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            Path("C:/Windows/Fonts/seguiemj.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
            Path("seguiemj.ttf"),
        ]
        if emoji
        else [
            Path("C:/Windows/Fonts/consola.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            Path("consola.ttf"),
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_sloth_rgba(size: int) -> Image.Image:
    sloth = "\U0001F9A5"
    font = load_font(size, emoji=True)
    canvas = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text((0, 0), sloth, font=font, embedded_color=True)
    bbox = canvas.getbbox()
    if not bbox:
        raise RuntimeError("Failed to render sloth emoji")
    return canvas.crop(bbox)


def to_bw_rgba(rgba: Image.Image) -> Image.Image:
    gray = rgba.convert("L")
    bw = gray.point(lambda x: 0 if x < 165 else 255, "1")
    result = Image.new("RGBA", bw.size, (0, 0, 0, 0))
    pixels = bw.load()
    for y in range(bw.size[1]):
        for x in range(bw.size[0]):
            if pixels[x, y] == 0:
                result.putpixel((x, y), DARK + (255,))
            else:
                result.putpixel((x, y), BG + (255,))
    return result


def draw_glasses_on_sloth(mark: Image.Image) -> Image.Image:
    """Draw round glasses on the sloth face (vector, aligned to eye region)."""
    img = mark.copy()
    draw = ImageDraw.Draw(img)
    sw, sh = img.size
    ey = int(sh * 0.435)
    radius = max(3, int(sw * 0.072))
    stroke = max(2, int(sw * 0.022))
    left_cx = int(sw * 0.185)
    right_cx = int(sw * 0.335)

    for cx in (left_cx, right_cx):
        draw.ellipse(
            [cx - radius, ey - radius, cx + radius, ey + radius],
            outline=DARK,
            width=stroke,
        )
    draw.line(
        [(left_cx + radius, ey), (right_cx - radius, ey)],
        fill=DARK,
        width=stroke,
    )
    return img


def center_mark(mode: str, render_size: int = 280) -> Image.Image:
    sloth = to_bw_rgba(render_sloth_rgba(render_size))
    if mode == "sloth":
        return sloth
    if mode == "sloth_glasses":
        return draw_glasses_on_sloth(sloth)
    raise ValueError(f"Unknown center mark: {mode}")


def generate_qr(
    url: str,
    out_path: Path,
    *,
    label: str | None = None,
    center: str = "sloth",
) -> Path:
    label = label or label_from_url(url)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=DARK, back_color=BG).convert("RGBA")

    mark = center_mark(center)
    qr_w, qr_h = qr_img.size
    target = int(min(qr_w, qr_h) * 0.28)
    mark = mark.resize((target, target), Image.LANCZOS)

    cx, cy = qr_w // 2, qr_h // 2
    pad = 10
    box = [
        cx - target // 2 - pad,
        cy - target // 2 - pad,
        cx + target // 2 + pad,
        cy + target // 2 + pad,
    ]
    draw = ImageDraw.Draw(qr_img)
    draw.rectangle(box, fill=BG + (255,))
    qr_img.paste(mark, (cx - target // 2, cy - target // 2), mark)

    url_font = load_font(18, emoji=False)
    text_bbox = draw.textbbox((0, 0), label, font=url_font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_padding = 16
    final_h = qr_h + text_h + text_padding * 2
    final = Image.new("RGB", (qr_w, final_h), BG)
    final.paste(qr_img.convert("RGB"), (0, 0))
    draw_final = ImageDraw.Draw(final)
    text_x = (qr_w - text_w) // 2
    text_y = qr_h + text_padding - text_bbox[1]
    draw_final.text((text_x, text_y), label, fill=DARK, font=url_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, "PNG")
    return out_path


def decode_qr_url(path: Path) -> str:
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError as exc:
        raise RuntimeError("Install pyzbar for verification: pip install pyzbar") from exc

    data = pyzbar_decode(Image.open(path))
    if not data:
        raise ValueError(f"No QR code found in {path}")
    return data[0].data.decode("utf-8")


def verify_file(path: Path, expected_url: str) -> None:
    decoded = decode_qr_url(path)
    if decoded.rstrip("/") != expected_url.rstrip("/"):
        raise ValueError(f"{path.name}: decoded {decoded!r} != expected {expected_url!r}")
    print(f"OK  {path.relative_to(REPO_ROOT)} -> {decoded}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate branded QR PNGs.")
    parser.add_argument(
        "--preset",
        choices=[*PRESETS.keys(), "all"],
        help="Built-in target (website, blog, or all).",
    )
    parser.add_argument("--url", help="URL to encode (overrides preset).")
    parser.add_argument("--out", type=Path, help="Output PNG path (overrides preset).")
    parser.add_argument(
        "--center",
        choices=("sloth", "sloth_glasses"),
        help="Center mark style (overrides preset).",
    )
    parser.add_argument("--label", help="Footer text (default: host/path from URL).")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Decode generated QR(s) and check URL (requires pyzbar).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.preset and not args.url:
        parser = argparse.ArgumentParser()
        print("Specify --preset {website,blog,all} or --url with --out", file=sys.stderr)
        return 1

    jobs: list[tuple[str, Path, str, str]] = []
    if args.preset == "all":
        for name, cfg in PRESETS.items():
            jobs.append((name, Path(cfg["out"]), cfg["url"], cfg["center"]))
    elif args.preset:
        cfg = PRESETS[args.preset]
        jobs.append(
            (
                args.preset,
                Path(args.out or cfg["out"]),
                args.url or cfg["url"],
                args.center or cfg["center"],
            )
        )
    elif args.url:
        if not args.out:
            print("--out is required when using --url without --preset", file=sys.stderr)
            return 1
        jobs.append(
            (
                "custom",
                args.out,
                args.url,
                args.center or "sloth",
            )
        )

    for name, out_path, url, center in jobs:
        saved = generate_qr(url, out_path, label=args.label, center=center)
        print(f"Wrote {saved.relative_to(REPO_ROOT)} ({center})")
        if args.verify:
            verify_file(saved, url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
