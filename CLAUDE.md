# CLAUDE.md

## Commands

```bash
uv sync --dev                        # install all dependencies
uv run pre-commit install            # wire up git hooks (once per clone)

uv run pytest                        # run all tests with coverage
uv run pytest tests/cli/             # run a single test directory
uv run pytest -k test_version        # run a single test by name

uv run ruff check                    # lint (src/ and tests/)
uv run ruff check --fix              # lint with auto-fix
uv run ruff format                   # format
uv run mypy                          # type-check (strict, src/ and tests/)

uv run perfectmind --help                 # run the CLI
uv run perfectmind swims list -d 2026-11-07 -l cornell   # live swim lookup (-t lane|endurance_lane|recreational)
uv run perfectmind mcp                    # MCP server on stdio
claude plugin validate .                  # validate plugin manifests
claude --plugin-dir .                     # try the plugin locally
```

## Project structure

`src/perfectmind/` follows a layered structure:

- **`config.py`** — frozen `Settings` (pydantic-settings, `LACUNA_` env prefix). Calls `load_dotenv()` at import time.
- **`client/`** — `PerfectMindClient(http, widget_id)`: one method per BookMe4 endpoint, no business logic. It takes an injected `httpx.AsyncClient` (with `base_url` set). `models.py` holds raw pydantic models (PascalCase aliases, `extra="ignore"`).
- **`service/swims.py`** — `SwimService(client)`: resolves the "Swimming" calendar and the swim program filters **by name** (never hard-code tenant GUIDs), queries one day with the date-range filter, follows `nextKey`, and maps to `SwimSession`. `SWIM_TYPE_MARKERS` (ordered: "endurance lane swim" before "lane swim") classifies both program and event names into `SwimType`. To support a new swim type, add a marker there. Raises `SwimServiceError` for user-facing errors.
- **`mcp/server.py`** — `build_server(service)` registers the tools on an `MCPServer` (mcp SDK **2.x**, not `FastMCP`). `run(settings)` is the composition root that builds the client from `Settings`. Tools convert `SwimServiceError` / `httpx.HTTPError` into `ToolError`.
- **`cli/app.py`** — Typer CLI. Sub-command groups live in separate files (e.g. `cli/swims.py`) and are registered via `app.add_typer(...)`. `perfectmind mcp` runs the server on stdio.

Plugin layout (repo root): `.claude-plugin/plugin.json` + `marketplace.json`, `.mcp.json` (starts `uv run --directory ${CLAUDE_PLUGIN_ROOT} perfectmind mcp`), `skills/perfectmind-swims/SKILL.md`. When a tool's behaviour or arguments change, update the skill too.

Logging is configured once in `__init__.py`: loguru handler removed and re-added with the level from `SETTINGS.log_level`. Set `LACUNA_LOG_LEVEL=DEBUG` to see debug output. Logs must go to **stderr**. stdout carries the MCP stdio protocol, so never `print()` in code reachable from `perfectmind mcp`.

Tests: `tests/conftest.py` has a `FakeSite` that serves `tests/fixtures/*.json` (trimmed real responses) through `httpx.MockTransport`. MCP tools are tested in-process with `mcp.client.Client(build_server(service))`.

## Commit Message Convention

This project follows **Conventional Commits** (https://www.conventionalcommits.org).
All commits generated or suggested by Claude must conform to this spec.

### Format
<type>[optional scope]: <description>
[optional body]
[optional footer(s)]

### Allowed types

- feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

### Scopes for this project (pick the closest match)

- python, research

### Rules

1. Subject line ≤ 72 characters, lowercase, no trailing period.
2. Use imperative mood: "add feature" not "added feature".
3. Breaking changes: append `!` to the type OR add a `BREAKING CHANGE:` footer.
4. Never squash unrelated changes into one commit — split them.

## Key conventions and guidelines

- Dependency injection: pass config explicitly to any client/service — never read the global `SETTINGS` inside library code.
- mypy is strict. All functions including tests need return type annotations.
- Git hooks (pre-commit) run ruff (fix + format) and mypy on every commit.
- CLI lazy imports: in `cli/app.py`, `perfectmind.*` imports must be inside the command function body, not at module level. `typer`, `rich`, and stdlib belong at the top of the file. This keeps `--help` fast and isolates heavy deps per command.
- **After every significant change** — new CLI command, new data pipeline, new dependency, changed directory layout — update `CLAUDE.md` (architecture / conventions) and `README.md` (user-facing instructions, dev setup, release process). Keep them in sync with the actual codebase.
