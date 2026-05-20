"""Parse the conferences section from index.html and write conferences.csv."""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = REPO_ROOT / "index.html"
CSV_PATH = REPO_ROOT / "assets" / "documents" / "conferences.csv"

CONF_BLOCK_RE = re.compile(
    r'<div class="publication-item conference-item">(.*?)</div>\s*</div>',
    re.DOTALL,
)
YEAR_RE = re.compile(r'<span class="conf-year">(.*?)</span>')
ROLE_RE = re.compile(r'<span class="conf-role[^"]*">(.*?)</span>')
TITLE_LINK_RE = re.compile(r'<h4><a\s+href="([^"]+)"[^>]*>(.*?)</a></h4>')
TITLE_PLAIN_RE = re.compile(r"<h4>(.*?)</h4>")
VENUE_RE = re.compile(r'<p class="pub-venue">(.*?)</p>')


def extract_conferences(html: str) -> list[dict]:
    section_match = re.search(
        r'<section id="conferences".*?</section>', html, re.DOTALL
    )
    if not section_match:
        raise SystemExit("Could not find the conferences section in index.html")

    section = section_match.group()
    rows = []

    for block in CONF_BLOCK_RE.finditer(section):
        content = block.group(1)

        year = YEAR_RE.search(content)
        role = ROLE_RE.search(content)
        venue = VENUE_RE.search(content)

        link_match = TITLE_LINK_RE.search(content)
        if link_match:
            link, title = link_match.group(1), link_match.group(2)
        else:
            title_match = TITLE_PLAIN_RE.search(content)
            title = title_match.group(1) if title_match else ""
            link = ""

        rows.append(
            {
                "Year": year.group(1).strip() if year else "",
                "Conference": title.strip(),
                "Venue": venue.group(1).strip() if venue else "",
                "Role": role.group(1).strip() if role else "",
                "Link": link.strip(),
            }
        )

    return rows


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    rows = extract_conferences(html)

    if not rows:
        raise SystemExit("No conferences found — aborting to avoid data loss")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Year", "Conference", "Venue", "Role", "Link"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} conferences to {CSV_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
