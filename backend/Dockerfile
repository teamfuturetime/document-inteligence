FROM python:3.14.5-slim
RUN pip install --no-cache-dir uv==0.12.22
WORKDIR /app
COPY backend/ /app/backend/
COPY data/ /app/data/
RUN uv sync --project backend --locked --no-dev
ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "docintel.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
