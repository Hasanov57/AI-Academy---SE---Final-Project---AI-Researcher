"""Run all five supplied questions and save JSON and Markdown artefacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from researcher.bootstrap import build_runtime
from researcher.config import Settings
from researcher.logging_config import configure_logging
from researcher.models import ResearchRequest
from researcher.rendering import render_markdown


async def run(offline: bool, output_dir: Path) -> None:
    """Execute the required five-question demonstration."""
    settings = Settings(storage_backend="memory" if offline else "postgres")
    configure_logging(settings.log_level)
    runtime = await build_runtime(settings, offline=offline)
    question_file = PROJECT_ROOT / "data" / "research_questions.json"
    questions = json.loads(question_file.read_text(encoding="utf-8"))["questions"]
    results = []
    try:
        for item in questions:
            result = await runtime.researcher.ask(
                ResearchRequest(question=item["text"], no_cache=True)
            )
            results.append(result)
            print(f"completed {item['id']}: {result.duration_ms:.0f} ms")
    finally:
        await runtime.close()

    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"research-run-{stamp}.json"
    markdown_path = output_dir / f"research-run-{stamp}.md"
    await asyncio.to_thread(
        json_path.write_text,
        json.dumps([json.loads(result.model_dump_json()) for result in results], indent=2),
        encoding="utf-8",
    )
    await asyncio.to_thread(
        markdown_path.write_text,
        "\n\n---\n\n".join(render_markdown(result) for result in results),
        encoding="utf-8",
    )
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("artefacts"))
    args = parser.parse_args()
    asyncio.run(run(args.offline, args.output_dir))


if __name__ == "__main__":
    main()
