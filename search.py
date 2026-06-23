"""Recherche par mots-clés dans les articles convertis en Markdown.

Outil simple et sans dépendance pour explorer les articles téléchargés sous
l'angle bug bounty : on cherche des termes (CVE, vulnérabilité, technique...)
et on affiche les passages correspondants avec leur contexte.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def search_file(path: Path, patterns: list[re.Pattern], context: int) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if any(p.search(line) for p in patterns):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            snippet = "\n".join(lines[start:end])
            hits.append((i + 1, snippet))
    return hits


def main() -> None:
    data_dir = os.environ.get("DATA_DIR", "data")
    parser = argparse.ArgumentParser(description="Recherche dans les articles Markdown.")
    parser.add_argument("terms", nargs="+", help="Termes à rechercher (OU logique).")
    parser.add_argument("--dir", default=f"{data_dir}/markdown", help="Répertoire Markdown.")
    parser.add_argument("--context", type=int, default=2, help="Lignes de contexte.")
    parser.add_argument(
        "--ignore-case", action="store_true", default=True, help="Insensible à la casse."
    )
    args = parser.parse_args()

    flags = re.IGNORECASE if args.ignore_case else 0
    patterns = [re.compile(re.escape(t), flags) for t in args.terms]

    md_dir = Path(args.dir)
    files = sorted(md_dir.glob("*.md"))
    if not files:
        print(f"Aucun fichier Markdown dans {md_dir}.")
        return

    total = 0
    for f in files:
        hits = search_file(f, patterns, args.context)
        if hits:
            print(f"\n=== {f.name} ({len(hits)} correspondance(s)) ===")
            for line_no, snippet in hits:
                print(f"--- ligne {line_no} ---")
                print(snippet)
            total += len(hits)

    print(f"\nTotal : {total} correspondance(s) dans {len(files)} fichier(s).")


if __name__ == "__main__":
    main()
