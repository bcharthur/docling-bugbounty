"""Récupération des articles scientifiques récents de cybersécurité sur arXiv.

Utilise l'API publique d'arXiv (http://export.arxiv.org/api/query) pour
interroger la catégorie cs.CR (Cryptography and Security) ainsi que quelques
catégories connexes, puis télécharge les PDF correspondants.
"""

from __future__ import annotations

import argparse
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import requests

ARXIV_API = "https://export.arxiv.org/api/query"

# Espaces de noms du flux Atom renvoyé par l'API arXiv.
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# Catégories arXiv pertinentes pour la cybersécurité.
#   cs.CR : Cryptography and Security  (la principale)
#   cs.NI : Networking and Internet Architecture
#   cs.SE : Software Engineering
DEFAULT_CATEGORIES = ["cs.CR"]

USER_AGENT = "docling-bugbounty/1.0 (research; +https://github.com/)"


@dataclass
class Paper:
    arxiv_id: str
    title: str
    summary: str
    authors: list[str]
    published: str
    pdf_url: str

    @property
    def safe_id(self) -> str:
        """Identifiant utilisable comme nom de fichier."""
        return self.arxiv_id.replace("/", "_")


def build_query(categories: list[str], keywords: str | None) -> str:
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    query = f"({cat_query})"
    if keywords:
        # Recherche dans titre + résumé.
        kw = " OR ".join(f'abs:"{k.strip()}"' for k in keywords.split(",") if k.strip())
        if kw:
            query = f"{query} AND ({kw})"
    return query


def search_arxiv(
    categories: list[str],
    max_results: int = 20,
    keywords: str | None = None,
) -> list[Paper]:
    """Interroge l'API arXiv et retourne les articles les plus récents."""
    params = {
        "search_query": build_query(categories, keywords),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }
    resp = requests.get(
        ARXIV_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    papers: list[Paper] = []
    for entry in root.findall("atom:entry", NS):
        entry_id = (entry.findtext("atom:id", default="", namespaces=NS) or "").strip()

        pdf_url = ""
        for link in entry.findall("atom:link", NS):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
        if not pdf_url and entry_id:
            # Fallback : reconstruit l'URL PDF depuis l'id.
            pdf_url = entry_id.replace("/abs/", "/pdf/")

        title = " ".join((entry.findtext("atom:title", "", NS) or "").split())
        summary = " ".join((entry.findtext("atom:summary", "", NS) or "").split())
        published = (entry.findtext("atom:published", "", NS) or "").strip()
        authors = [
            (name.text or "").strip()
            for name in entry.findall("atom:author/atom:name", NS)
        ]

        arxiv_id = entry_id.rsplit("/abs/", 1)[-1]
        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                summary=summary,
                authors=authors,
                published=published,
                pdf_url=pdf_url,
            )
        )
    return papers


def download_pdf(paper: Paper, dest_dir: Path, overwrite: bool = False) -> Path | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{paper.safe_id}.pdf"
    if dest.exists() and not overwrite:
        print(f"  [skip] déjà présent : {dest.name}")
        return dest

    try:
        with requests.get(
            paper.pdf_url, headers={"User-Agent": USER_AGENT}, timeout=120, stream=True
        ) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.RequestException as exc:
        print(f"  [erreur] téléchargement {paper.arxiv_id} : {exc}")
        return None

    print(f"  [ok] {dest.name}")
    # On reste poli avec l'API d'arXiv.
    time.sleep(1)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Récupère les articles arXiv récents.")
    parser.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help="Catégories arXiv séparées par des virgules (def: cs.CR).",
    )
    parser.add_argument(
        "--max-results", type=int, default=20, help="Nombre d'articles à récupérer."
    )
    parser.add_argument(
        "--keywords",
        default=None,
        help='Mots-clés optionnels (ex: "fuzzing,web,authentication").',
    )
    parser.add_argument(
        "--out",
        default=os.environ.get("DATA_DIR", "data") + "/pdfs",
        help="Répertoire de sortie pour les PDF.",
    )
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    print(f"Recherche arXiv : catégories={categories} max={args.max_results}")
    papers = search_arxiv(categories, args.max_results, args.keywords)
    print(f"{len(papers)} article(s) trouvé(s). Téléchargement...")

    out_dir = Path(args.out)
    for paper in papers:
        print(f"- {paper.arxiv_id} : {paper.title[:80]}")
        download_pdf(paper, out_dir)


if __name__ == "__main__":
    main()
