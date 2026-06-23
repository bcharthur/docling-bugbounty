"""Pipeline complète : récupération arXiv -> conversion docling.

Point d'entrée par défaut du conteneur Docker. Enchaîne le téléchargement des
articles récents de cybersécurité et leur conversion en Markdown.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from convert import convert_pdf
from fetch_arxiv import DEFAULT_CATEGORIES, download_pdf, search_arxiv

from docling.document_converter import DocumentConverter


def main() -> None:
    data_dir = os.environ.get("DATA_DIR", "data")
    parser = argparse.ArgumentParser(description="Pipeline arXiv -> docling.")
    parser.add_argument("--categories", default=",".join(DEFAULT_CATEGORIES))
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--keywords", default=None)
    parser.add_argument("--data-dir", default=data_dir)
    args = parser.parse_args()

    pdf_dir = Path(args.data_dir) / "pdfs"
    md_dir = Path(args.data_dir) / "markdown"
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    print("=" * 60)
    print("ÉTAPE 1/2 : Récupération des articles arXiv")
    print("=" * 60)
    papers = search_arxiv(categories, args.max_results, args.keywords)
    print(f"{len(papers)} article(s) trouvé(s).")
    pdfs: list[Path] = []
    for paper in papers:
        print(f"- {paper.arxiv_id} : {paper.title[:80]}")
        pdf = download_pdf(paper, pdf_dir)
        if pdf:
            pdfs.append(pdf)

    print()
    print("=" * 60)
    print("ÉTAPE 2/2 : Conversion en Markdown via docling")
    print("=" * 60)
    if not pdfs:
        print("Aucun PDF à convertir.")
        return
    converter = DocumentConverter()
    for pdf in pdfs:
        print(f"- {pdf.name}")
        convert_pdf(converter, pdf, md_dir)

    print()
    print(f"Terminé. Markdown disponible dans {md_dir}.")
    print('Recherche : python search.py "CVE" "authentication bypass"')


if __name__ == "__main__":
    main()
