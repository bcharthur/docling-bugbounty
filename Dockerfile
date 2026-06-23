# Image pour exécuter docling et la pipeline de récupération d'articles arXiv.
FROM python:3.11-slim

# Dépendances système utiles à docling (rendu PDF, OpenCV, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
        tesseract-ocr \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On installe les dépendances Python d'abord pour profiter du cache Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-téléchargement des modèles docling pour éviter de le faire à chaque run.
# Tolérant aux erreurs réseau pendant le build : les modèles seront sinon
# téléchargés au premier lancement.
RUN docling-tools models download || true

COPY . .

# Répertoire de travail pour les données (PDF + markdown).
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data/pdfs /app/data/markdown

# Par défaut on lance la pipeline complète (fetch -> convert).
ENTRYPOINT ["python", "pipeline.py"]
CMD ["--max-results", "20"]
