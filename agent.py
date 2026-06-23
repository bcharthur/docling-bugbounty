"""Agent Claude qui raisonne sur le corpus d'articles converti par docling.

Architecture :

    Claude  <-->  outils (list/search/read)  <-->  Markdown produit par docling

Claude dispose de trois outils pour explorer le corpus à la demande (plutôt que
de tout charger en contexte) :
  - list_documents  : lister les articles disponibles
  - search_corpus   : recherche par mots-clés dans tous les articles
  - read_document   : lire un article (paginé)

On lui fournit la mission de bug bounty et le périmètre (scope) autorisé /
interdit. Claude lit les articles pertinents et propose des pistes de
vulnérabilités à investiguer **dans les limites du scope fourni**.

Usage :
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py --scope scope.md "Trouve des pistes de faille web reportables"
    python agent.py            # mode interactif
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import anthropic
from anthropic import beta_tool

MODEL = "claude-opus-4-8"

# Répertoire du corpus Markdown (configuré dans main()).
MARKDOWN_DIR = Path(os.environ.get("DATA_DIR", "data")) / "markdown"

SYSTEM_PROMPT = """\
Tu es un assistant de recherche en sécurité offensive qui aide à préparer une \
campagne de bug bounty (par ex. sur YesWeHack), de façon responsable et légale.

Tu disposes d'un corpus d'articles scientifiques récents de cybersécurité \
(catégorie arXiv cs.CR), convertis en Markdown. Utilise tes outils pour :
  - lister les articles (list_documents) ;
  - chercher des techniques/sujets pertinents (search_corpus) ;
  - lire en détail les articles utiles (read_document).

Ta mission : à partir de ces articles et du périmètre (scope) fourni par \
l'utilisateur, proposer des **pistes de vulnérabilités à investiguer** et une \
méthodologie de test.

Règles impératives :
  - Respecte strictement le scope : ne propose JAMAIS de tester ce qui est hors \
    périmètre ou explicitement interdit.
  - Reste au niveau méthodologie et classes de vulnérabilités (où chercher, \
    quoi tester, comment, quels signaux). Ne fournis pas d'exploit clé en main \
    contre une cible réelle nommée.
  - Cite les articles sur lesquels tu t'appuies (nom de fichier / titre).
  - Rappelle que tout test doit se faire uniquement sur des cibles autorisées \
    par le programme.
"""


@beta_tool
def list_documents() -> str:
    """Liste les articles disponibles dans le corpus.

    Retourne, pour chaque fichier Markdown, son nom et son premier titre
    (généralement le titre de l'article).
    """
    files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not files:
        return f"Aucun article dans {MARKDOWN_DIR}. Lance d'abord la pipeline docling."
    lines = []
    for f in files:
        title = ""
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s:
                title = s.lstrip("# ").strip()
                break
        lines.append(f"- {f.name} : {title[:120]}")
    return f"{len(files)} article(s) :\n" + "\n".join(lines)


@beta_tool
def search_corpus(query: str, max_results: int = 30) -> str:
    """Recherche un terme (insensible à la casse) dans tous les articles.

    Args:
        query: Le terme ou la sous-chaîne à chercher (ex: "SSRF", "deserialization").
        max_results: Nombre maximum de correspondances à retourner.
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[str] = []
    for f in sorted(MARKDOWN_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                hits.append(f"[{f.name}:{i + 1}] {line.strip()[:200]}")
                if len(hits) >= max_results:
                    return f"{len(hits)} correspondance(s) (limite atteinte) :\n" + "\n".join(hits)
    if not hits:
        return f"Aucune correspondance pour « {query} »."
    return f"{len(hits)} correspondance(s) :\n" + "\n".join(hits)


@beta_tool
def read_document(name: str, offset: int = 0, limit: int = 400) -> str:
    """Lit un article du corpus (paginé pour ménager le contexte).

    Args:
        name: Nom du fichier Markdown (ex: "2606.23130v1.md").
        offset: Ligne de départ (0-indexée).
        limit: Nombre de lignes à retourner.
    """
    path = MARKDOWN_DIR / Path(name).name  # empêche toute traversée de chemin
    if not path.exists():
        return f"Introuvable : {name}. Utilise list_documents pour voir les fichiers."
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    chunk = lines[offset : offset + limit]
    header = f"{name} — lignes {offset}..{offset + len(chunk)} sur {len(lines)}\n"
    suffix = ""
    if offset + limit < len(lines):
        suffix = f"\n\n[... suite : read_document(name='{name}', offset={offset + limit}) ...]"
    return header + "\n".join(chunk) + suffix


def run_agent(client: anthropic.Anthropic, messages: list[dict]) -> str:
    """Lance le tool runner et retourne la réponse texte finale de Claude."""
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        tools=[list_documents, search_corpus, read_document],
        messages=messages,
    )
    final_text = ""
    for message in runner:
        for block in message.content:
            if block.type == "text" and block.text.strip():
                print(block.text, flush=True)
                final_text = block.text
            elif block.type == "tool_use":
                print(f"  · [outil] {block.name}({block.input})", flush=True)
    return final_text


def build_user_message(task: str, scope: str | None) -> str:
    if scope:
        return (
            "Voici le périmètre (scope) du programme de bug bounty. "
            "Tout ce qui n'y est pas autorisé est hors-scope :\n\n"
            f"```\n{scope}\n```\n\n"
            f"Mission : {task}"
        )
    return task


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Claude sur le corpus docling.")
    parser.add_argument("task", nargs="?", help="La mission (sinon mode interactif).")
    parser.add_argument(
        "--scope",
        help="Fichier décrivant le scope autorisé/interdit (texte ou Markdown).",
    )
    parser.add_argument(
        "--dir", help="Répertoire du corpus Markdown (def: $DATA_DIR/markdown)."
    )
    args = parser.parse_args()

    global MARKDOWN_DIR
    if args.dir:
        MARKDOWN_DIR = Path(args.dir)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Erreur : exporte ANTHROPIC_API_KEY avant de lancer l'agent.")
        raise SystemExit(1)

    scope_text = None
    if args.scope:
        scope_text = Path(args.scope).read_text(encoding="utf-8", errors="ignore")

    client = anthropic.Anthropic()
    messages: list[dict] = []

    if args.task:
        messages.append({"role": "user", "content": build_user_message(args.task, scope_text)})
        run_agent(client, messages)
        return

    # Mode interactif : conversation multi-tours.
    print("Agent bug bounty (corpus docling). Tape 'quit' pour sortir.")
    first = True
    while True:
        try:
            user = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"quit", "exit", "q"}:
            break
        if not user:
            continue
        content = build_user_message(user, scope_text) if first else user
        first = False
        messages.append({"role": "user", "content": content})
        # On laisse le tool runner gérer la boucle ; on relance avec l'historique.
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=SYSTEM_PROMPT,
            tools=[list_documents, search_corpus, read_document],
            messages=messages,
        )
        last = None
        for message in runner:
            last = message
            for block in message.content:
                if block.type == "text" and block.text.strip():
                    print(block.text, flush=True)
                elif block.type == "tool_use":
                    print(f"  · [outil] {block.name}({block.input})", flush=True)
        if last is not None:
            messages.append({"role": "assistant", "content": last.content})


if __name__ == "__main__":
    main()
