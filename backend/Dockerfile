FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install the CPU-only torch wheel first so the image stays lean — the default
# PyPI torch pulls ~2GB of CUDA libraries the FinBERT scorer doesn't use.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# Bake the FinBERT weights into the image so the first news fetch doesn't have to
# download ~440MB at runtime (and the container works even if HF Hub is slow).
# Non-fatal: if the prebake can't reach HF Hub during build, the model downloads
# lazily at runtime instead (with the lexicon as fallback), so the build still ships.
RUN python -c "from transformers import pipeline; pipeline('text-classification', model='ProsusAI/finbert', top_k=None)" || echo "FinBERT prebake skipped — will download at runtime"

COPY . .

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
