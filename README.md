# Async Research Assistant

Async Research Assistant is a Python application that answers research questions using information from Wikipedia, arXiv and web search.

The three sources are queried concurrently. Their results are combined into one concise answer using Gemini, with numeric citations and links to the original sources.

## Main features

- Concurrent source retrieval with `asyncio`
- Wikipedia, arXiv and Tavily web search
- Answers with inline numeric citations
- Retries, timeouts and graceful handling of failed sources
- PostgreSQL storage and a 24-hour source cache
- Command-line interface and Streamlit interface
- Docker Compose setup
- Offline tests without live-network dependencies

The course-provided `ai/` package is used without changing its public interface. The project adds the surrounding configuration, concurrency, storage, validation, reliability and user-interface layers.

## Project structure

```text
ai/                    Course-provided AI package
src/researcher/        Main application
tests/                 Offline test suite
scripts/               Demo, benchmark and storage checks
data/                  Example research questions
artefacts/             Saved demonstration results
report/                Final project report
presentation/          Project-day presentation
Dockerfile             Application container
docker-compose.yml     Application, UI and PostgreSQL services
```

## How to use

### 1. Prepare the environment file

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and provide:

- `GOOGLE_API_KEY`
- `TAVILY_API_KEY`
- A value for `POSTGRES_PASSWORD`
- The same password inside `DATABASE_URL`
- A real contact email inside `HTTP_USER_AGENT`

Never commit `.env` to GitHub.

### 2. Run the Streamlit interface with Docker

```powershell
docker compose up --build -d db ui
```

Open the following address in a browser:

```text
http://localhost:8501
```

### 3. Ask a question from the command line

```powershell
docker compose run --rm researcher python -m researcher ask "What are the latest developments in nuclear fusion energy?"
```

Use only selected sources:

```powershell
docker compose run --rm researcher python -m researcher ask "What is low-rank adaptation?" --sources wiki,arxiv
```

Bypass the source cache:

```powershell
docker compose run --rm researcher python -m researcher ask "What is quantum computing?" --no-cache
```

### 4. Run the demonstration

```powershell
docker compose run --rm researcher python scripts/demo.py
```

### 5. Stop the containers

```powershell
docker compose down
```

For a completely offline installation check:

```powershell
docker compose run --rm researcher python -m researcher ask "What is photosynthesis?" --offline --storage memory
```

## Testing and quality checks

The automated suite does not require live network access:

```powershell
python -m pytest --cov=researcher --cov-report=term-missing --cov-fail-under=60
python -m ruff check src tests scripts
python -m mypy src/researcher
python demo_ai.py --offline --limit 5
```

The final verification completed **64 tests** with **73.56% branch-aware coverage**. Ruff and strict mypy completed without issues.

## Sequential versus concurrent benchmark

The benchmark compares fetching Wikipedia, arXiv and web-search results sequentially with fetching the same sources concurrently. Application cache reads and writes are bypassed, and LLM synthesis is excluded so the source-retrieval pipeline is measured directly.

```powershell
docker compose build researcher
docker compose up -d db
docker compose run --rm researcher python scripts/bench.py --runs 3
```

| Run | Sequential | Concurrent |
|---:|---:|---:|
| 1 | 1.440 s | 0.535 s |
| 2 | 1.439 s | 0.544 s |
| 3 | 1.523 s | 0.677 s |
| **Median** | **1.440 s** | **0.544 s** |

The median concurrent run was **2.64x faster**. After parallelization, the main bottleneck is the slowest external provider plus normal network latency variation.
