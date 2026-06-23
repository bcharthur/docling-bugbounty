"""Conversion des PDF arXiv en Markdown via docling.

docling extrait la structure du document (titres, paragraphes, tableaux,
formules) et produit un Markdown propre, beaucoup plus exploitable pour la
recherche que le texte brut d'un PDF.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def build_converter(do_ocr: bool = False) -> DocumentConverter:
    """Construit un DocumentConverter adapté aux PDF arXiv.

    Les articles arXiv sont des PDF "born-digital" : ils possèdent déjà une
    couche texte native. L'OCR est donc inutile et, par défaut, l'engine OCR de
    docling (RapidOCR/PP-OCRv6) échoue sur certaines configurations torch
    (« Unsupported configuration: torch.PP-OCRv6.det.small »). On le désactive,
    ce qui supprime l'erreur et accélère nettement la conversion.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )



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

    print(f"{len(pdfs)} PDF à convertir. Initialisation de docling (OCR désactivé)...")
    converter = build_converter(do_ocr=False)

    out_dir = Path(args.out)
    for pdf in pdfs:
        print(f"- {pdf.name}")
        convert_pdf(converter, pdf, out_dir)


if __name__ == "__main__":
    main()
