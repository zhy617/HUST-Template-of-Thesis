from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        print(
            "pdftoppm was not found; PDF figures will be used only if Pandoc can read them directly. "
            "Install Poppler or provide same-name PNG/SVG files for robust DOCX export.",
            file=sys.stderr,
        )
        return 0

    out_root = root / ".docx-build" / "pdf-images"
    images_dir = root / "images"
    pdfs = sorted(images_dir.glob("*.pdf")) if images_dir.exists() else []
    converted = 0
    for pdf in pdfs:
        rel = pdf.relative_to(root)
        target = out_root / rel.with_suffix(".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = target.with_suffix("")
        subprocess.run(
            [pdftoppm, "-png", "-singlefile", "-r", "220", str(pdf), str(prefix)],
            check=True,
        )
        converted += 1

    print(f"Prepared {converted} PDF figure fallback PNG files in {out_root}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
