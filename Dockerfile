FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd --system researcher \
    && useradd --system --gid researcher --create-home researcher

COPY requirements.txt pyproject.toml ./
RUN python -m pip install --upgrade pip==26.0.1 \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY ai ./ai
COPY src ./src
COPY data ./data
COPY scripts ./scripts
COPY README.md ./README.md

RUN python -m pip install --no-deps . \
    && chown -R researcher:researcher /app

USER researcher

EXPOSE 8501

CMD ["python", "-m", "researcher", "ask", "What is photosynthesis and what are its main stages?"]
