# Personal website

Academic portfolio for Modafar Al-Shouha.

**Live site:** https://modafarshouha.github.io/modafarshouha/

Static HTML/CSS site hosted on GitHub Pages. Conference data in `index.html` is synced to `assets/documents/conferences.csv` via `scripts/sync_conferences.py`. Branded QR images are regenerated with `python scripts/generate_qr.py --preset all --verify` (requires `qrcode`, `Pillow`, and `pyzbar` for `--verify`).
