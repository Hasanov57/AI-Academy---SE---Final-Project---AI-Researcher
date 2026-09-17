"""Build the report and defense slide PDFs in environments without LaTeX."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).parents[1]
BLUE = colors.HexColor("#00459A")
DARK_BLUE = colors.HexColor("#163A63")
LIGHT_BLUE = colors.HexColor("#EAF2FB")
RED = colors.HexColor("#9E1B1B")
GRAY = colors.HexColor("#5A6570")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
DARK_GRAY = colors.HexColor("#20252A")


def _register_fonts() -> tuple[str, str]:
    """Use a Unicode-safe bundled Windows font when available."""
    regular_path = Path("C:/Windows/Fonts/arial.ttf")
    bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular_path.exists() and bold_path.exists():
        pdfmetrics.registerFont(TTFont("ProjectSans", regular_path))
        pdfmetrics.registerFont(TTFont("ProjectSans-Bold", bold_path))
        return "ProjectSans", "ProjectSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = _register_fonts()


def _report_header_footer(page_canvas: canvas.Canvas, doc: BaseDocTemplate) -> None:
    page_canvas.saveState()
    width, height = A4
    page_canvas.setStrokeColor(colors.HexColor("#AAB2BA"))
    page_canvas.line(2.2 * cm, height - 1.25 * cm, width - 2.2 * cm, height - 1.25 * cm)
    page_canvas.setFont(FONT, 7.5)
    page_canvas.setFillColor(GRAY)
    page_canvas.drawString(2.2 * cm, height - 1.05 * cm, "AI-ENG-110 - Final Report")
    page_canvas.drawRightString(width - 2.2 * cm, height - 1.05 * cm, "Spring 2026")
    page_canvas.line(2.2 * cm, 1.35 * cm, width - 2.2 * cm, 1.35 * cm)
    page_canvas.drawString(2.2 * cm, 1.05 * cm, "AI Academy, National AI Center")
    page_canvas.drawRightString(width - 2.2 * cm, 1.05 * cm, f"Page {doc.page} of 10")
    page_canvas.restoreState()


def _report_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ProjectTitle",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=21,
            leading=25,
            textColor=BLUE,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "ProjectSubtitle",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=GRAY,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=15,
            leading=18,
            textColor=BLUE,
            spaceBefore=3,
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=13,
            textColor=DARK_BLUE,
            spaceBefore=7,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName=FONT,
            fontSize=8.7,
            leading=12.2,
            textColor=colors.HexColor("#20252A"),
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName=FONT,
            fontSize=7.7,
            leading=10.2,
            textColor=colors.HexColor("#303840"),
            spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=styles["BodyText"],
            fontName=FONT,
            fontSize=8.4,
            leading=11.5,
            leftIndent=8,
            rightIndent=8,
            borderColor=BLUE,
            borderWidth=0.8,
            borderPadding=8,
            backColor=LIGHT_BLUE,
            spaceAfter=9,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.7,
            leading=8.6,
            leftIndent=8,
            rightIndent=8,
            borderColor=colors.HexColor("#D5DBE1"),
            borderWidth=0.5,
            borderPadding=7,
            backColor=LIGHT_GRAY,
            spaceBefore=4,
            spaceAfter=8,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"- {text}", style)


def build_report() -> Path:
    """Create the ten-page technical report."""
    output = ROOT / "report" / "report.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = _report_styles()
    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=1.65 * cm,
        bottomMargin=1.7 * cm,
        title="AI-ENG-110 Final Project Report - Async Research Assistant",
        author="Samir Həsənov, Ramil Məmmədəliyev, Elmir Əsgərov",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=_report_header_footer))

    story = []
    story.extend(
        [
            Spacer(1, 0.55 * cm),
            _p("AI Academy, National AI Center", styles["subtitle"]),
            _p("AI-ENG-110 Software Engineering - Final Project", styles["subtitle"]),
            _p("Async Research Assistant", styles["title"]),
            Table(
                [
                    ["Team", "Async Research Assistant Team", "Topic", "4"],
                    [
                        "Members",
                        "Samir Həsənov; Ramil Məmmədəliyev; Elmir Əsgərov",
                        "Date",
                        "2026-09-17",
                    ],
                    [
                        "Repository",
                        _p(
                            "github.com/Hasanov57/AI-Academy---SE---Final-Project---AI-Researcher",
                            styles["small"],
                        ),
                        "",
                        "",
                    ],
                    ["Tag", "v1.0-final", "Term", "Spring 2026"],
                ],
                colWidths=[2.2 * cm, 7.3 * cm, 1.8 * cm, 3.1 * cm],
                style=TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), FONT),
                        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
                        ("SPAN", (1, 2), (3, 2)),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LINEABOVE", (0, 0), (-1, 0), 0.7, GRAY),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.7, GRAY),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Spacer(1, 0.45 * cm),
            _p("Executive Summary", styles["h1"]),
            _p(
                "We built a command-line research assistant that queries Wikipedia, arXiv and "
                "Tavily concurrently and produces a concise answer with numeric citations. The "
                "student-owned layer wraps the supplied <font name='Courier'>ai/</font> package "
                "without changing its interface. It adds typed configuration, PostgreSQL "
                "persistence, a TTL cache, retries, timeouts, rate limiting and structured "
                "logging. A bounded asyncio pipeline isolates failed sources so remaining "
                "evidence can still reach synthesis. The live benchmark measured 1.440 seconds "
                "sequentially and 0.544 seconds concurrently, a 2.64x speedup with application "
                "caching disabled, while sixty-two offline tests pass with 78.25 percent coverage. "
                "A real Gemini request incompatibility taught us to keep provider adaptations "
                "outside the supplied package; if starting again, we would enforce that boundary "
                "from the first commit and add semantic citation-entailment checks.",
                styles["callout"],
            ),
            _p("Contents", styles["h1"]),
            Table(
                [
                    ["1", "Project Overview", "2"],
                    ["2", "Architecture", "3-4"],
                    ["3", "Concurrency and Performance", "5"],
                    ["4", "Robustness and Error Handling", "6"],
                    ["5", "Storage and Caching", "7"],
                    ["6", "Testing", "8"],
                    ["7", "Deployment and Reproducibility", "9"],
                    ["8", "Limitations, Tools and Benchmark Appendix", "10"],
                ],
                colWidths=[0.8 * cm, 12.5 * cm, 1.1 * cm],
                style=TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), FONT),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("TEXTCOLOR", (1, 0), (1, -1), BLUE),
                        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.5, GRAY),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("1. Project Overview", styles["h1"]),
            _p("1.1 Problem framing and scope", styles["h2"]),
            _p(
                "The user submits one research question. The application searches three "
                "different evidence channels in parallel, merges usable excerpts and asks the "
                "provided synthesizer to write one short answer. The response contains inline "
                "numeric markers, reference titles and URLs, source timings and warnings for "
                "upstream failures.",
                styles["body"],
            ),
            _p(
                "The required entry point is <font name='Courier'>python -m researcher ask "
                "\"question\"</font>. The <font name='Courier'>--sources wiki,arxiv</font> option "
                "restricts retrieval, while <font name='Courier'>--no-cache</font> forces a fresh "
                "run. JSON output supports saved artefacts and automated inspection. The first "
                "release intentionally omits a web interface because Topic 4 requires a CLI and "
                "only recommends HTTP.",
                styles["body"],
            ),
            _p("1.2 Provider choice and the AI module contract", styles["h2"]),
            _p(
                "Google Gemini gemini-3.5-flash-lite performs synthesis because the supplied "
                "adapter "
                "supports structured output and its free tier controls cost. Tavily supplies "
                "general web results. Wikipedia and arXiv require no credentials. PostgreSQL is "
                "local during development and accessed asynchronously through asyncpg.",
                styles["body"],
            ),
            _p(
                "Every external research call crosses the instructor-owned API: "
                "<font name='Courier'>ai.fetch_wikipedia</font>, "
                "<font name='Courier'>ai.fetch_arxiv</font>, "
                "<font name='Courier'>ai.fetch_web</font> or "
                "<font name='Courier'>ai.synthesize</font>. Our composition root instantiates "
                "the supplied provider adapters with validated secrets. The student package does "
                "not call provider SDKs or source endpoints directly.",
                styles["callout"],
            ),
            _p("Inputs and outputs", styles["h2"]),
            Table(
                [
                    ["Boundary", "Validated input", "Typed output"],
                    ["CLI", "Question, source subset, cache flag", "Exit code and rendered result"],
                    ["Core", "ResearchRequest", "ResearchResult"],
                    ["Source wrapper", "SourceName and canonical query", "SourceFetchOutcome"],
                    ["Provided AI", "Question and Source list", "AnswerWithCitations"],
                    ["Repository", "ResearchResult or cache entry", "Stored row or cache hit"],
                ],
                colWidths=[3.0 * cm, 6.0 * cm, 5.3 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            Spacer(1, 0.25 * cm),
            _p(
                "Semantic defense: after the provided schema validation, the wrapper checks "
                "marker ranges, marker-to-reference equality and a citation on each substantive "
                "sentence. Invalid output triggers another synthesis attempt.",
                styles["small"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("2. Architecture", styles["h1"]),
            _p("2.1 Module map", styles["h2"]),
            Preformatted(
                """User
  |
  v
CLI -> Researcher -> SourceOrchestrator -- semaphore=3 --+
  |                                                      +-> SourceService(wiki)
  |                                                      +-> SourceService(arxiv)
  |                                                      +-> SourceService(web)
  |                                                                |
  |                                                cache/retry/timeout/logging
  |                                                                |
  |                                                        provided ai.fetch_*
  +-> SynthesisService -> provided ai.synthesize -> Citation validator
  +-> PostgreSQL session, source, attempt, citation and cache tables""",
                styles["code"],
            ),
            _p(
                "The horizontal boundary above <font name='Courier'>provided ai</font> belongs to "
                "the team. The code below it remains unchanged. Network and LLM behaviour enter "
                "only through injected callables, making the boundary easy to mock.",
                styles["callout"],
            ),
            _p("2.2 Module-by-module responsibilities", styles["h2"]),
            Table(
                [
                    ["Module", "Owned responsibility"],
                    ["config.py", "Typed environment configuration and live credential checks."],
                    ["models.py", "Pydantic contracts for requests, outcomes and results."],
                    [
                        "source_service.py",
                        "TTL cache, retry, timeout, rate-limit and call logging.",
                    ],
                    ["orchestrator.py", "Shared HTTP client, bounded tasks and failure isolation."],
                    [
                        "synthesis_service.py",
                        "Thread offload, timeout, retry and citation validation.",
                    ],
                    ["researcher.py", "Complete use case, URL de-duplication and persistence."],
                    ["storage/", "PostgreSQL implementation plus memory test substitute."],
                    ["cli.py", "Argument validation, result rendering and clean exit codes."],
                ],
                colWidths=[4.4 * cm, 9.9 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("2.3 OOP design and data flow", styles["h1"]),
            _p("Student-owned abstraction", styles["h2"]),
            _p(
                "ResearchRepository is an abstract base class because every runtime needs the "
                "same cache lifecycle, result transaction and resource cleanup operations. "
                "PostgresRepository implements durable production behaviour. MemoryRepository "
                "implements identical semantics for offline demonstrations and fast unit tests. "
                "The base class prevents the core use case from depending on asyncpg.",
                styles["body"],
            ),
            Preformatted(
                """class ResearchRepository(ABC):
    async def get_cached_sources(source, query_key): ...
    async def put_cached_sources(source, query_key, sources, ttl): ...
    async def save_result(result): ...

class PostgresRepository(ResearchRepository): ...
class MemoryRepository(ResearchRepository): ...""",
                styles["code"],
            ),
            _p("Composition and pure functions", styles["h2"]),
            _p(
                "Researcher receives an orchestrator, synthesis service and repository through "
                "its constructor. SourceService receives a map of fetch callables. This "
                "composition is more appropriate than inheritance because these objects "
                "collaborate but do not represent subtypes of one another. Stateful behaviour "
                "lives in classes. Query canonicalization, URL normalization and de-duplication "
                "remain pure functions.",
                styles["body"],
            ),
            _p("Data flow across boundaries", styles["h2"]),
            Table(
                [
                    ["Step", "Contract", "Reason"],
                    ["1", "ResearchRequest", "Normalizes question and source subset."],
                    ["2", "SourceFetchOutcome", "Carries results, cache status, time and error."],
                    ["3", "list[Source]", "Uses the provided immutable schema without wrapping."],
                    ["4", "AnswerWithCitations", "Preserves the instructor synthesis contract."],
                    ["5", "ResearchResult", "Adds audit metadata and degradation warnings."],
                ],
                colWidths=[1.1 * cm, 4.6 * cm, 8.6 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            _p(
                "No naked dictionary crosses a service boundary. Dictionaries appear only while "
                "serializing JSONB or JSON artefacts.",
                styles["callout"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("3. Concurrency and Performance", styles["h1"]),
            _p("3.1 Why asyncio", styles["h2"]),
            _p(
                "Wikipedia, arXiv and web search spend most of their time waiting for remote I/O. "
                "Native asyncio tasks therefore avoid the process startup and serialization costs "
                "of multiprocessing. The orchestrator shares one httpx connection pool and "
                "creates one task per selected origin. A configurable semaphore prevents "
                "unbounded work if the source set expands.",
                styles["body"],
            ),
            _p(
                "The supplied synthesis interface is synchronous. asyncio.to_thread moves that "
                "blocking SDK call away from the event loop without bypassing the provided "
                "adapter. This keeps the concurrency model honest: native async for HTTP and a "
                "thread only where the dependency forces it.",
                styles["body"],
            ),
            _p("3.2 Sequential versus concurrent benchmark", styles["h2"]),
            Table(
                [
                    ["Run", "Sequential (s)", "Concurrent (s)"],
                    ["1", "1.440", "0.535"],
                    ["2", "1.439", "0.544"],
                    ["3", "1.523", "0.677"],
                    ["Median", "1.440", "0.544"],
                ],
                colWidths=[4.3 * cm, 5.0 * cm, 5.0 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            Spacer(1, 0.18 * cm),
            _p(
                "Speedup = 1.440 / 0.544 = <b>2.64x</b>. Three live retrieval runs used all "
                "sources on the same Windows machine with application caching disabled. The "
                "measurement isolates retrieval and excludes LLM synthesis; network and provider "
                "caches can still introduce normal variation.",
                styles["callout"],
            ),
            _p("3.3 Rate limit and politeness", styles["h2"]),
            _bullet(
                "arXiv calls reserve a minimum one-second interval per process.", styles["body"]
            ),
            _bullet("A semaphore limits simultaneous sources to three by default.", styles["body"]),
            _bullet(
                "HTTP 429 and provider failures enter exponential retry up to three attempts.",
                styles["body"],
            ),
            _bullet(
                "Per-source timing identifies the new bottleneck after parallelization.",
                styles["body"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("4. Robustness and Error Handling", styles["h1"]),
            _p("4.1 Wrapping the AI module", styles["h2"]),
            Table(
                [
                    ["Concern", "Implementation"],
                    [
                        "Retry",
                        "Tenacity exponential wait; ProviderError, HTTP and timeout failures.",
                    ],
                    ["Timeout", "Separate source and synthesis limits with asyncio.timeout."],
                    [
                        "Logging",
                        "INFO timing/count events, DEBUG payloads, WARNING source failures.",
                    ],
                    [
                        "Rate limit",
                        "Semaphore, arXiv minimum interval and retry after provider 429.",
                    ],
                    ["Validation", "Pydantic input plus semantic citation checks."],
                    ["Degradation", "Typed failed outcome; sibling tasks and synthesis continue."],
                ],
                colWidths=[3.1 * cm, 11.2 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            _p("4.2 Concrete failure exercise", styles["h2"]),
            _p(
                "A live Gemini request returned HTTP 400 because a provider-specific thinking "
                "option was incompatible with the selected model. The CLI showed a clean provider "
                "error and the logs identified the status without exposing the key. We restored "
                "the supplied adapter to the course version and added a student-owned ResearchLLM "
                "wrapper, preserving the instructor package boundary.",
                styles["body"],
            ),
            _p(
                "The incident corrected an early attempt to solve model compatibility inside the "
                "provided package. Moving the adaptation into student-owned code protected the "
                "course contract. Separate injected-failure tests verify that an exhausted source "
                "retry becomes a warning while sibling results still reach synthesis.",
                styles["callout"],
            ),
            _p("4.3 Input and output validation", styles["h2"]),
            _bullet(
                "Questions are trimmed, whitespace-normalized and limited to 1,000 characters.",
                styles["body"],
            ),
            _bullet(
                "At least one unique selector from wiki, arxiv or web is required.", styles["body"]
            ),
            _bullet("Missing live credentials fail before any external call.", styles["body"]),
            _bullet(
                "Citation markers must be present, in range and equal the returned reference set.",
                styles["body"],
            ),
            _bullet(
                "Every substantive sentence must include a valid citation marker.", styles["body"]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("5. Storage and Caching", styles["h1"]),
            _p("5.1 PostgreSQL schema", styles["h2"]),
            Table(
                [
                    ["Table", "Source of truth", "Important constraints"],
                    [
                        "research_sessions",
                        "Question, answer, warnings, total time",
                        "UUID primary key",
                    ],
                    [
                        "research_sources",
                        "Ordered title, URL and excerpt",
                        "Session FK plus ordinal",
                    ],
                    [
                        "source_attempts",
                        "Cache flag, duration, error, count",
                        "Session plus origin key",
                    ],
                    ["citations", "Marker to source-row mapping", "Two-column foreign key"],
                    ["source_cache", "Serialized Source list", "Origin/query key and expiry index"],
                ],
                colWidths=[3.3 * cm, 6.1 * cm, 4.9 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            _p(
                "One transaction inserts a completed session, its ordered sources, source "
                "attempt telemetry and citations. Cascading foreign keys prevent orphaned rows. "
                "Cache expiry and session creation timestamps have indexes because those are the "
                "main operational lookup paths.",
                styles["body"],
            ),
            _p("5.2 Caching policy", styles["h2"]),
            _p(
                "The key combines SourceName with a canonical query produced by case-folding, "
                "trimming and collapsing whitespace. This makes equivalent capitalization and "
                "spacing hit the same entry. Each JSONB payload contains validated Source models. "
                "The default TTL is 86,400 seconds and remains configurable from the environment.",
                styles["body"],
            ),
            _p(
                "Expired rows are deleted lazily during lookup. A cache miss invokes the source "
                "and stores even an empty successful result, preventing repeated requests for a "
                "valid no-result query. The no-cache flag bypasses both reads and writes, which "
                "keeps benchmark runs comparable and lets users demand fresh evidence. A dedicated "
                "two-pass verification produced a 100 percent hit rate on its second pass.",
                styles["callout"],
            ),
            _p("Stored versus derived values", styles["h2"]),
            _bullet(
                "Provider excerpts and final answers are stored as evidence of the exact run.",
                styles["body"],
            ),
            _bullet(
                "Cache-hit status and timings are observed values stored per attempt.",
                styles["body"],
            ),
            _bullet(
                "Speedup, source totals and rendered CLI text are derived and not stored.",
                styles["body"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("6. Testing", styles["h1"]),
            _p("6.1 Strategy and coverage", styles["h2"]),
            Table(
                [
                    ["Suite", "Count", "Network", "Result"],
                    ["Instructor AI smoke contract", "Included", "Mocked", "Passing"],
                    ["Student-owned tests", "Included", "Replaced boundaries", "Passing"],
                    ["Total", "62", "None", "78.25% coverage"],
                ],
                colWidths=[6.2 * cm, 2.1 * cm, 3.0 * cm, 3.0 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            _p(
                "Coverage uses branch measurement over the researcher package. PostgreSQL error "
                "branches account for most uncovered lines because the local unit suite does not "
                "pretend a memory fake validates asyncpg protocol details. The documented Docker "
                "Compose smoke procedure is the final integration check.",
                styles["body"],
            ),
            _p("6.2 Notable tests", styles["h2"]),
            _bullet(
                "Happy path: one Wikipedia result reaches synthesis and persistence.",
                styles["body"],
            ),
            _bullet(
                "Concurrency: three delayed fetchers overlap and beat the sequential wall clock.",
                styles["body"],
            ),
            _bullet(
                "Degradation: arXiv raises while Wikipedia still produces a result.", styles["body"]
            ),
            _bullet(
                "Retry: two transient failures precede a successful third call.", styles["body"]
            ),
            _bullet(
                "Timeout: repeated deadline exhaustion surfaces after the retry budget.",
                styles["body"],
            ),
            _bullet(
                "Citation output: missing, dangling and mismatched markers are rejected.",
                styles["body"],
            ),
            _bullet(
                "Cache: canonical-equivalent queries hit and zero-TTL entries expire.",
                styles["body"],
            ),
            _p("Quality commands", styles["h2"]),
            Preformatted(
                """pytest --cov=researcher --cov-report=term-missing --cov-fail-under=60
ruff check src tests scripts
mypy src/researcher
python demo_ai.py --offline --limit 5""",
                styles["code"],
            ),
            _p(
                "Ruff and strict mypy complete without issues. The instructor smoke tests remain "
                "unchanged and pass inside the same full suite.",
                styles["callout"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("7. Deployment and Reproducibility", styles["h1"]),
            _p("7.1 Docker image", styles["h2"]),
            _p(
                "The single-stage 515.4 MB image uses Python 3.12 slim, installs fully pinned "
                "dependencies, copies the "
                "provided and student packages, and drops to a non-root user. Docker Compose runs "
                "PostgreSQL 17.6 Alpine and waits for pg_isready before the application starts.",
                styles["body"],
            ),
            Preformatted(
                """docker build -t async-researcher .
docker compose up -d db
docker compose run --rm researcher

docker run --rm async-researcher python -m researcher ask \\
  "What is photosynthesis?" --offline --storage memory""",
                styles["code"],
            ),
            _p("7.2 Configuration", styles["h2"]),
            Table(
                [
                    ["Group", "Variables"],
                    ["LLM choice", _p("LLM_PROVIDER, LLM_MODEL", styles["small"])],
                    [
                        "LLM keys",
                        _p("GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY", styles["small"]),
                    ],
                    [
                        "Web",
                        _p("WEB_SEARCH_PROVIDER, TAVILY_API_KEY, SERPER_API_KEY", styles["small"]),
                    ],
                    [
                        "Storage",
                        _p(
                            "DATABASE_URL, STORAGE_BACKEND, POSTGRES_PASSWORD, CACHE_TTL_SECONDS",
                            styles["small"],
                        ),
                    ],
                    [
                        "Timeouts",
                        _p(
                            "PER_SOURCE_TIMEOUT_SECONDS, SYNTHESIS_TIMEOUT_SECONDS",
                            styles["small"],
                        ),
                    ],
                    [
                        "Retries",
                        _p(
                            "MAX_RETRY_ATTEMPTS, RETRY_MIN_WAIT_SECONDS, RETRY_MAX_WAIT_SECONDS",
                            styles["small"],
                        ),
                    ],
                    [
                        "Limits",
                        _p(
                            "MAX_PARALLEL_SOURCES, MAX_SOURCES_PER_QUERY, "
                            "ARXIV_MIN_INTERVAL_SECONDS",
                            styles["small"],
                        ),
                    ],
                    [
                        "Interface",
                        _p("LOG_LEVEL, QUESTION_MAX_LENGTH, HTTP_USER_AGENT", styles["small"]),
                    ],
                ],
                colWidths=[3.2 * cm, 11.1 * cm],
                repeatRows=1,
                style=_table_style(),
            ),
            _p(
                "Secrets use Pydantic SecretStr, never appear in INFO logs and live only in the "
                "ignored .env file. A missing key for the selected live provider or a missing "
                "Compose password fails before work begins. Other settings have typed defaults; "
                "out-of-range or malformed values fail Pydantic validation with a clear message.",
                styles["callout"],
            ),
            _p("Reproducibility controls", styles["h2"]),
            _bullet("Every dependency uses an exact version.", styles["body"]),
            _bullet(
                "The package exposes both python -m researcher and a console script.",
                styles["body"],
            ),
            _bullet(
                "Offline mode verifies installation without credentials or network.", styles["body"]
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("8. Limitations and Future Work", styles["h1"]),
            _bullet("Citation syntax checks cannot prove semantic entailment.", styles["body"]),
            _bullet(
                "A single PostgreSQL instance has no replication or automated backup.",
                styles["body"],
            ),
            _bullet(
                "In-process arXiv limiting does not coordinate multiple containers.", styles["body"]
            ),
            _bullet(
                "Provider excerpts can omit context even when all systems are healthy.",
                styles["body"],
            ),
            _bullet(
                "Provider failover, streaming and a web interface remain outside release 1.0.",
                styles["body"],
            ),
            _p("Tools and Acknowledgements", styles["h1"]),
            _p(
                "OpenAI Codex was used substantially to draft architecture, implementation, tests, "
                "Docker troubleshooting and report text. The team reviewed and adapted the drafts, "
                "executed the complete offline suite and live demonstrations, and accepts "
                "responsibility for understanding and defending the submission. The provided ai "
                "package and course templates came from AI Academy.",
                styles["callout"],
            ),
            _p("References", styles["h1"]),
            _p("[1] AI Academy, AI-ENG-110 Final Project Brief, Spring 2026.", styles["small"]),
            _p(
                "[2] Gemini model documentation: "
                "ai.google.dev/gemini-api/docs",
                styles["small"],
            ),
            _p("[3] Tavily API documentation: docs.tavily.com", styles["small"]),
            _p(
                "[4] MediaWiki API documentation: mediawiki.org/wiki/API:Main_page",
                styles["small"],
            ),
            _p(
                "[5] arXiv API documentation: info.arxiv.org/help/api/index.html",
                styles["small"],
            ),
            _p(
                "[6] Python asyncio documentation: docs.python.org/3/library/asyncio.html",
                styles["small"],
            ),
            _p("Appendix - Reproducing the benchmark", styles["h1"]),
            Preformatted(
                """docker compose build researcher
docker compose up -d db
docker compose run --rm researcher python scripts/bench.py --runs 3""",
                styles["code"],
            ),
            _p(
                "The live command requires the Gemini and Tavily keys in .env even though only "
                "source timing enters the benchmark composition root. Run both modes on the same "
                "machine with caches bypassed and record the raw table.",
                styles["small"],
            ),
            Spacer(1, 0.45 * cm),
            _p("End of report", styles["subtitle"]),
        ]
    )

    doc.build(story)
    return output


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 7.4),
            ("LEADING", (0, 0), (-1, -1), 9.2),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C0C8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _slide_header(c: canvas.Canvas, title: str, page_number: int, total: int = 11) -> None:
    width, height = landscape((7.5 * 72, 13.333 * 72))
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.setFont(FONT_BOLD, 22)
    c.drawString(34, height - 46, title)
    c.setStrokeColor(colors.HexColor("#D0D6DC"))
    c.line(34, 31, width - 34, 31)
    c.setFont(FONT, 7)
    c.setFillColor(GRAY)
    c.drawString(34, 18, "Async Research Assistant Team - Topic 4")
    c.drawRightString(width - 34, 18, f"AI-ENG-110 - Spring 2026  {page_number}/{total}")


def _slide_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    size: float = 17,
    leading: float = 23,
    color: colors.Color = DARK_GRAY,
    bold: bool = False,
) -> float:
    font = FONT_BOLD if bold else FONT
    c.setFont(font, size)
    c.setFillColor(color)
    char_width = max(20, int(width / (size * 0.53)))
    for line in wrap(text, width=char_width, break_long_words=False):
        c.drawString(x, y, line)
        y -= leading
    return y


def _slide_bullets(
    c: canvas.Canvas,
    items: list[str],
    x: float,
    y: float,
    width: float,
    *,
    size: float = 16,
) -> float:
    for item in items:
        c.setFillColor(BLUE)
        c.circle(x + 4, y + 5, 3, fill=1, stroke=0)
        y = _slide_text(c, item, x + 18, y, width - 18, size=size, leading=size + 6)
        y -= 10
    return y


def _box(c: canvas.Canvas, x: float, y: float, w: float, h: float, text: str) -> None:
    c.setFillColor(LIGHT_BLUE)
    c.setStrokeColor(BLUE)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
    c.setFillColor(DARK_BLUE)
    c.setFont(FONT_BOLD, 12)
    lines = wrap(text, width=max(12, int(w / 7)))
    ty = y + h / 2 + (len(lines) - 1) * 7
    for line in lines:
        c.drawCentredString(x + w / 2, ty, line)
        ty -= 14


def build_slides() -> Path:
    """Create an eleven-slide PDF following the supplied Beamer visual style."""
    output = ROOT / "presentation" / "slides.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    page_size = landscape((7.5 * 72, 13.333 * 72))
    width, height = page_size
    c = canvas.Canvas(
        str(output),
        pagesize=page_size,
        pageCompression=1,
        metadata={"Title": "Async Research Assistant Defense", "Author": "Topic 4 Team"},
    )

    # Slide 1
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.setFont(FONT_BOLD, 34)
    c.drawCentredString(width / 2, height * 0.62, "Async Research Assistant")
    c.setStrokeColor(GRAY)
    c.line(width * 0.31, height * 0.55, width * 0.69, height * 0.55)
    c.setFillColor(GRAY)
    c.setFont(FONT, 16)
    c.drawCentredString(width / 2, height * 0.47, "AI-ENG-110 Software Engineering Final Project")
    c.setFont(FONT_BOLD, 15)
    c.setFillColor(RED)
    c.drawCentredString(width / 2, height * 0.37, "Async Research Assistant Team")
    c.setFont(FONT, 10)
    c.setFillColor(GRAY)
    c.drawCentredString(width / 2, 25, "AI Academy, National AI Center - Spring 2026")
    c.showPage()

    # Slide 2
    _slide_header(c, "The problem", 2)
    _slide_text(
        c,
        "A research question should produce one concise answer grounded in "
        "evidence from three different source types.",
        54,
        height - 105,
        width - 108,
        size=22,
        leading=30,
        bold=True,
        color=DARK_BLUE,
    )
    _slide_bullets(
        c,
        [
            "Input: a validated question and optional source subset.",
            "Sources: Wikipedia, arXiv and Tavily queried in parallel.",
            "Output: cited answer, reference URLs, timings and degradation warnings.",
            'Entry point: python -m researcher ask "question".',
        ],
        66,
        height - 220,
        width - 132,
    )
    c.showPage()

    # Slide 3
    _slide_header(c, "Architecture", 3)
    _box(c, 50, 385, 145, 48, "CLI")
    _box(c, 255, 385, 165, 48, "Researcher")
    _box(c, 480, 385, 205, 48, "SourceOrchestrator")
    _box(c, 745, 385, 165, 48, "SourceService")
    _box(c, 160, 255, 205, 55, "PostgreSQL audit")
    _box(c, 480, 255, 205, 55, "SynthesisService")
    _box(c, 745, 255, 165, 55, "provided ai/")
    c.setStrokeColor(GRAY)
    c.setLineWidth(1.6)
    for x1, y1, x2, y2 in [
        (195, 409, 255, 409),
        (420, 409, 480, 409),
        (685, 409, 745, 409),
        (337, 385, 262, 310),
        (337, 385, 582, 310),
        (685, 282, 745, 282),
        (827, 385, 827, 310),
    ]:
        c.line(x1, y1, x2, y2)
    _slide_text(
        c,
        "Our code owns every box except the supplied ai package. Constructor "
        "injection keeps that boundary testable.",
        80,
        165,
        width - 160,
        size=17,
        leading=23,
        color=GRAY,
    )
    c.showPage()

    # Slide 4
    _slide_header(c, "Three design decisions", 4)
    decisions = [
        ("1", "Async source I/O", "Independent HTTP waits overlap under a configurable semaphore."),
        (
            "2",
            "Repository abstraction",
            "PostgreSQL is durable; memory follows the same contract in tests.",
        ),
        (
            "3",
            "Strict AI boundary",
            "Retries and validation wrap ai.fetch_* and ai.synthesize without edits.",
        ),
    ]
    y = height - 120
    for number, heading, body in decisions:
        c.setFillColor(BLUE)
        c.circle(78, y + 8, 20, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 17)
        c.drawCentredString(78, y + 2, number)
        _slide_text(c, heading, 120, y + 14, 270, size=19, bold=True, color=DARK_BLUE)
        _slide_text(c, body, 400, y + 14, width - 455, size=16, leading=22)
        y -= 125
    c.showPage()

    # Slide 5
    _slide_header(c, "Concurrency benchmark", 5)
    c.setFont(FONT, 15)
    c.setFillColor(GRAY)
    c.drawString(55, height - 92, "Median of three identical runs, cache bypassed")
    chart_x, chart_y, chart_w, chart_h = 105, 120, 420, 300
    c.setStrokeColor(GRAY)
    c.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    c.line(chart_x, chart_y, chart_x + chart_w, chart_y)
    values = [("Sequential", 0.775, RED), ("Concurrent", 0.506, BLUE)]
    scale = chart_h / 0.9
    for index, (label, value, color) in enumerate(values):
        x = chart_x + 85 + index * 180
        bar_h = value * scale
        c.setFillColor(color)
        c.rect(x, chart_y, 95, bar_h, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#20252A"))
        c.setFont(FONT_BOLD, 16)
        c.drawCentredString(x + 47.5, chart_y + bar_h + 12, f"{value:.3f}s")
        c.setFont(FONT, 13)
        c.drawCentredString(x + 47.5, chart_y - 25, label)
    c.setFillColor(DARK_BLUE)
    c.setFont(FONT_BOLD, 30)
    c.drawString(625, 330, "1.53x")
    c.setFont(FONT, 17)
    c.setFillColor(GRAY)
    c.drawString(625, 300, "measured speedup")
    _slide_text(
        c,
        "After parallelization, the slowest source and provider limits replace "
        "summed latency as the bottleneck.",
        625,
        245,
        270,
        size=16,
        leading=22,
    )
    c.showPage()

    # Slide 6
    _slide_header(c, "Graceful degradation", 6)
    _slide_text(
        c,
        "Injected incident: arXiv raises ProviderError while Wikipedia succeeds.",
        55,
        height - 105,
        width - 110,
        size=21,
        leading=28,
        bold=True,
        color=DARK_BLUE,
    )
    _slide_bullets(
        c,
        [
            "The retry budget expires with exponential backoff.",
            "The orchestrator records a typed failure instead of cancelling sibling tasks.",
            "Wikipedia evidence still reaches synthesis.",
            "The final answer prints and stores an explicit arXiv warning.",
        ],
        70,
        height - 205,
        width - 140,
        size=17,
    )
    c.showPage()

    # Slide 7
    _slide_header(c, "Scripted demonstration", 7)
    c.setFillColor(LIGHT_GRAY)
    c.setStrokeColor(colors.HexColor("#C8D0D8"))
    c.roundRect(55, 255, width - 110, 200, 6, fill=1, stroke=1)
    code_lines = [
        "$ python -m researcher ask",
        '  "How do transformer models handle long context?"',
        "",
        '$ python -m researcher ask "How does CRISPR-Cas9 work?"',
        "  --sources wiki,arxiv --no-cache",
    ]
    c.setFont("Courier", 16)
    c.setFillColor(colors.HexColor("#20252A"))
    y = 415
    for line in code_lines:
        c.drawString(78, y, line)
        y -= 30
    _slide_text(
        c,
        "The five-question script also saves JSON and Markdown evidence under artefacts/.",
        65,
        185,
        width - 130,
        size=18,
        leading=25,
        color=DARK_BLUE,
    )
    c.showPage()

    # Slide 8
    _slide_header(c, "Testing", 8)
    metrics = [
        ("46", "offline tests"),
        ("73%", "student-package coverage"),
        ("16", "contract tests retained"),
    ]
    x = 75
    for value, label in metrics:
        c.setFillColor(BLUE)
        c.setFont(FONT_BOLD, 34)
        c.drawString(x, height - 150, value)
        c.setFillColor(GRAY)
        c.setFont(FONT, 14)
        c.drawString(x, height - 178, label)
        x += 300
    _slide_bullets(
        c,
        [
            "Happy path persists a cited result.",
            "Concurrency test observes three overlapping source tasks.",
            "Timeout, retry and all-source failure paths are covered.",
            "Ruff and strict mypy complete without issues.",
        ],
        70,
        height - 260,
        width - 140,
        size=16,
    )
    c.showPage()

    # Slide 9
    _slide_header(c, "Storage and cache", 9)
    _slide_text(
        c,
        "PostgreSQL keeps the evidence needed to reproduce and explain each answer.",
        55,
        height - 105,
        width - 110,
        size=21,
        leading=28,
        bold=True,
        color=DARK_BLUE,
    )
    _slide_bullets(
        c,
        [
            "Sessions store the question, final answer, warnings and total time.",
            "Ordered sources and citation rows preserve numeric reference mapping.",
            "Source attempts store cache status, result count, time and failure detail.",
            "The source/query cache uses JSONB and a configurable 24-hour TTL.",
            "--no-cache bypasses reads and writes for fresh evidence and benchmarks.",
        ],
        70,
        height - 200,
        width - 140,
        size=16,
    )
    c.showPage()

    # Slide 10
    _slide_header(c, "Limitations", 10)
    _slide_bullets(
        c,
        [
            "Citation syntax checks cannot prove that an excerpt entails a claim.",
            "One PostgreSQL instance has no replication or automated backup.",
            "In-process arXiv limiting does not coordinate multiple containers.",
            "Upstream excerpts can omit context even when all services are healthy.",
            "Provider failover, streaming and a web interface remain future work.",
        ],
        70,
        height - 115,
        width - 140,
        size=17,
    )
    c.showPage()

    # Slide 11
    _slide_header(c, "Team ownership", 11)
    _slide_bullets(
        c,
        [
            "Workstream A: configuration, PostgreSQL and TTL cache.",
            "Workstream B: wrappers, retries, rate limits and orchestration.",
            "Workstream C: core use case, citation checks, CLI, tests and artefacts.",
            "Every pull request receives teammate review; all members can defend the architecture.",
        ],
        70,
        height - 120,
        width - 140,
        size=16,
    )
    c.setFillColor(BLUE)
    c.setFont(FONT_BOLD, 30)
    c.drawCentredString(width / 2, 100, "Questions?")
    c.showPage()
    c.save()
    return output


def main() -> None:
    report = build_report()
    slides = build_slides()
    print(report.relative_to(ROOT))
    print(slides.relative_to(ROOT))


if __name__ == "__main__":
    main()
