# Ekatra – one container: React website + FastAPI backend on port 7860 (Hugging Face Spaces / Render / any Docker host)
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 HF_HOME=/app/.hf PORT=7860 USE_E5=on
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
# CPU-only PyTorch keeps the image small; sentence-transformers runs the multilingual-e5 name matcher
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt sentence-transformers
# download the name-matching model once, at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small', device='cpu')"
COPY . .
COPY --from=web /web/dist frontend/dist
RUN cp data/ekatra.clean.db data/ekatra.db && chmod -R a+rwX /app
WORKDIR /app/backend
EXPOSE 7860
# every start begins from the clean demo database
CMD ["sh", "-c", "cp ../data/ekatra.clean.db ../data/ekatra.db && uvicorn serve:web --host 0.0.0.0 --port ${PORT}"]
