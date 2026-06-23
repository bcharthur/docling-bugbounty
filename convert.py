"""Conversion des PDF arXiv en Markdown via docling.

docling extrait la structure du document (titres, paragraphes, tableaux,
formules) et produit un Markdown propre, beaucoup plus exploitable pour la
recherche que le texte brut d'un PDF.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from docling.document_converter import DocumentConverter


def convert_pdf(converter: DocumentConverter, pdf_path: Path, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pdf_path.stem}.md"
    if out_path.exists():
        print(f"  [skip] déjà converti : {out_path.name}")
        return out_path

    try:
        result = converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()
    except Exception as exc:  # docling peut lever divers types d'erreurs
        print(f"  [erreur] conversion {pdf_path.name} : {exc}")
        return None

    out_path.write_text(markdown, encoding="utf-8")
    print(f"  [ok] {out_path.name} ({len(markdown)} caractères)")
    return out_path


def main() -> None:
    data_dir = os.environ.get("DATA_DIR", "data")
    parser = argparse.ArgumentParser(description="Convertit les PDF en Markdown via docling.")
    parser.add_argument("--pdf-dir", default=f"{data_dir}/pdfs", help="Répertoire des PDF.")
    parser.add_argument(
        "--out", default=f"{data_dir}/markdown", help="Répertoire de sortie Markdown."
    )
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"Aucun PDF trouvé dans {pdf_dir}. Lance d'abord fetch_arxiv.py.")
        return

    print(f"{len(pdfs)} PDF à convertir. Initialisation de docling...")
    converter = DocumentConverter()

    out_dir = Path(args.out)
    for pdf in pdfs:
        print(f"- {pdf.name}")
        convert_pdf(converter, pdf, out_dir)


if __name__ == "__main__":
    main()
