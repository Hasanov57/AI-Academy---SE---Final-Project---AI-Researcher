# Technical verification - 2026-09-16

- Docker Desktop engine recovered by moving stale socket directories aside. No volumes were reset.
- Application image built successfully from python:3.12-slim.
- PostgreSQL 17.6 container healthy.
- Standalone offline container CLI passed.
- Real PostgreSQL verification passed: cache miss then hit, expiry, persistence after reconnect,
  two saved sessions and their references.
- Five live questions completed with Gemini 3.5 Flash-Lite and Tavily, using all three source adapters.
- Database query after verification: 7 sessions, 43 source rows, 20 citations, 3 cache-hit attempts.
- Live answers: research-run-20260916T140735Z.json and .md in this directory.
- Supplied ai/*.py files and tests/test_ai_smoke.py byte-match SWENG_FinalProject.zip.
- Final automated suite: 62 tests passed with 78.25% coverage.
- Ruff style checks and mypy type checks passed with no issues.
- Final rebuilt image passed the standalone offline CLI and real PostgreSQL verification.
- API-key scan found no Gemini or Tavily key patterns outside the ignored `.env` file.

## Live retrieval benchmark

Command: `docker compose run --rm researcher python scripts/bench.py --runs 3`

| Run | Sequential seconds | Concurrent seconds |
|---|---:|---:|
| 1 | 1.440 | 0.535 |
| 2 | 1.439 | 0.544 |
| 3 | 1.523 | 0.677 |

Median: 1.440 seconds sequential, 0.544 seconds concurrent, 2.64x speedup.
Same question, sources and machine; application cache disabled. Measures retrieval, not LLM synthesis.
External services may cache requests; latency varies between runs.

## Scope

This verifies the technical application. Report, slides, signed contributions, GitHub collaboration,
final tag and submission packaging remain separate finalization work.
