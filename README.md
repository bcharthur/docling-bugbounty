# docling-bugbounty

Pipeline pour récupérer les **articles scientifiques récents de cybersécurité**
sur [arXiv](https://arxiv.org/) (catégorie `cs.CR`), les convertir en Markdown
exploitable avec [**docling**](https://github.com/docling-project/docling), puis
y faire des recherches ciblées dans une optique **bug bounty** (YesWeHack &co).

## Pourquoi docling ?

Le texte brut extrait d'un PDF est souvent illisible (colonnes mélangées,
tableaux cassés, notes de bas de page intercalées). docling reconstruit la
structure du document (titres, paragraphes, tableaux, formules) et produit un
Markdown propre, bien plus pertinent pour la recherche et l'analyse.

## Composants

| Fichier            | Rôle                                                            |
|--------------------|-----------------------------------------------------------------|
| `fetch_arxiv.py`   | Interroge l'API arXiv et télécharge les PDF récents.            |
| `convert.py`       | Convertit les PDF en Markdown via docling.                      |
| `pipeline.py`      | Enchaîne fetch + convert (point d'entrée du conteneur).         |
| `search.py`        | Recherche par mots-clés dans les Markdown générés.             |
| `agent.py`         | Agent Claude qui raisonne sur le corpus (bug bounty).          |
| `Dockerfile`       | Image contenant docling et toutes les dépendances.             |
| `docker-compose.yml` | Lancement simplifié avec persistance des données.            |

## Utilisation avec Docker

### Build

```bash
docker build -t docling-bugbounty .
```

> Le build installe docling (et PyTorch), puis pré-télécharge les modèles de
> mise en page. La première image est volumineuse (~plusieurs Go) ; c'est
> normal pour docling.

### Lancer la pipeline complète

```bash
# Récupère 20 articles cs.CR récents et les convertit en Markdown
docker run --rm -v "$(pwd)/data:/app/data" docling-bugbounty --max-results 20
```

Ou via docker-compose :

```bash
docker compose run --rm docling-bugbounty --max-results 30 --keywords "fuzzing,web,authentication"
```

Les fichiers atterrissent dans :
- `data/pdfs/`     : les PDF bruts
- `data/markdown/` : le Markdown produit par docling

### Rechercher dans les articles

```bash
docker run --rm -v "$(pwd)/data:/app/data" --entrypoint python docling-bugbounty \
  search.py "SQL injection" "SSRF" "authentication bypass"
```

## Utilisation locale (sans Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Récupérer les articles récents
python fetch_arxiv.py --max-results 20 --categories cs.CR

# 2. Convertir en Markdown
python convert.py

# 3. Chercher des pistes
python search.py "CVE" "remote code execution" "deserialization"
```

## Options utiles

`fetch_arxiv.py` / `pipeline.py` :

- `--categories` : catégories arXiv séparées par virgules (def. `cs.CR`).
  Autres pertinentes : `cs.NI` (réseau), `cs.SE` (génie logiciel).
- `--max-results` : nombre d'articles (def. 20).
- `--keywords`   : filtre par mots-clés sur le résumé,
  ex. `--keywords "smart contract,web,LLM"`.

## Agent Claude : `claude <-> docling <-> PDFs`

Une fois les articles convertis, `agent.py` branche l'API Claude sur le corpus.
Claude dispose de trois outils pour explorer les Markdown **à la demande**
(plutôt que de tout charger en contexte, ce qui exploserait pour des dizaines
de papiers) :

- `list_documents` — lister les articles et leur titre
- `search_corpus` — recherche par mots-clés dans tout le corpus
- `read_document` — lire un article (paginé)

Tu lui donnes une mission + le périmètre (scope) du programme, et il propose des
pistes de vulnérabilités à investiguer **en respectant le scope**.

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Mission ponctuelle, avec un fichier de scope
python agent.py --scope scope.example.md \
  "À partir des articles, propose 3 pistes de failles web reportables et la méthodo de test"

# Mode interactif (conversation multi-tours)
python agent.py --scope scope.example.md
```

Avec Docker (on passe la clé API et le corpus en volume) :

```bash
docker run --rm -it \
  -e ANTHROPIC_API_KEY \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/scope.example.md:/app/scope.md" \
  --entrypoint python docling-bugbounty \
  agent.py --scope scope.md "Propose des pistes de failles reportables"
```

Détails techniques :
- Modèle **`claude-opus-4-8`** avec *thinking* adaptatif et `effort: high`.
- Boucle d'outils gérée par le **tool runner** du SDK Anthropic (`beta_tool`).
- `read_document` filtre le nom de fichier pour empêcher toute traversée de chemin.

> ⚠️ Usage responsable : l'agent produit de la **méthodologie** et des classes de
> vulnérabilités à partir de la littérature. Tout test doit se faire uniquement
> sur des cibles **autorisées** par le programme YesWeHack et dans son scope.

## OCR désactivé par défaut

Les articles arXiv sont des PDF « born-digital » : ils ont déjà une couche
texte. L'OCR est donc inutile et il est désactivé (`do_ocr=False` dans
`build_converter`). Cela évite l'erreur
`Unsupported configuration: torch.PP-OCRv6.det.small` de l'engine OCR par défaut
et accélère nettement la conversion. Pour traiter des PDF scannés, réactive
l'OCR en passant `do_ocr=True`.

## Note

arXiv impose des règles d'usage de son API (pas de scraping massif). Le script
respecte un délai entre les téléchargements. Reste raisonnable sur le nombre de
requêtes.
