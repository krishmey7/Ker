"""Extrait le texte du PDF pour analyse (usage local)."""
import sys
from pathlib import Path

PDF = Path(r"e:\Mes Documents\Ce que j'aurais aimé savoir avant de me marier.pdf")
OUT = Path(__file__).resolve().parent.parent / "apps" / "game" / "data" / "_book_extract.txt"


def main():
    try:
        import pypdf
    except ImportError:
        print("pip install pypdf", file=sys.stderr)
        sys.exit(1)
    reader = pypdf.PdfReader(str(PDF))
    parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        parts.append(f"\n--- page {i + 1} ---\n{text}")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {len(parts)} pages to {OUT}")


if __name__ == "__main__":
    main()
