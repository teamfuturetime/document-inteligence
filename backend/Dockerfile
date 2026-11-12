FROM python:3.14.5-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.22
WORKDIR /app
COPY backend/ /app/backend/
COPY pipeline/ /app/pipeline/
COPY data/ /app/data/
RUN uv sync --project backend --locked --no-dev
ENV PATH="/app/backend/.venv/bin:$PATH"
COPY scripts/fetch_ocr_models.py /app/scripts/fetch_ocr_models.py
RUN python scripts/fetch_ocr_models.py --directory /opt/docintel-models \
    && useradd --uid 10001 --create-home docintel \
    && mkdir -p /app/runtime && chown docintel:docintel /app/runtime
ENV DOCINTEL_PROVIDER_MODE=tesseract \
    DOCINTEL_TESSDATA_DIR=/opt/docintel-models \
    DOCINTEL_RUNTIME_DIR=/app/runtime
USER docintel
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
EXPOSE 8000
CMD ["uvicorn", "docintel.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "16"]
