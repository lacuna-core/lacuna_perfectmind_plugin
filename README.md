# perfectmind

A Claude Code plugin for the [City of Markham PerfectMind booking site](https://cityofmarkham.perfectmind.com). It has an MCP server that wraps the site's public booking endpoints, and a skill that teaches Claude how to use it.

**Current scope:** read-only listing of drop-in **swims** (Lane, Endurance Lane and Recreational Swim) for a given date, with each session labelled by type. No login, no booking.

## Prerequisites

- [uv](https://docs.astral.sh/uv/): the MCP server runs with `uv run`
- Claude Code

## Install the plugin

From GitHub (Claude Code 2.1.275 or later):

```
/plugin install perfectmind --marketplace lacuna-core/lacuna_perfectmind_plugin
```

On older versions: `/plugin marketplace add lacuna-core/lacuna_perfectmind_plugin`, then `/plugin install perfectmind@perfectmind`.

From a local clone, for development:

```bash
claude --plugin-dir /path/to/lacuna_perfectmind_plugin

#or
claude plugin marketplace add ./
claude plugin install perfectmind@perfectmind

```

Then ask, for example: *"Any lane swims at Cornell tomorrow evening?"* or *"Rec swims on Saturday?"*

The plugin contains:

| Path | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `.claude-plugin/marketplace.json` | Lets the repo act as a single-plugin marketplace |
| `.mcp.json` | Starts the server: `uv run --directory ${CLAUDE_PLUGIN_ROOT} perfectmind mcp` (stdio) |
| `skills/perfectmind-swims/SKILL.md` | Tells Claude when and how to call the tool |

### MCP tools

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_swims` | `date` (YYYY-MM-DD), `location` (optional substring, e.g. `"Pan Am"`), `swim_types` (optional subset of `lane`, `endurance_lane`, `recreational`) | Sessions with `swim_type`, program name, start/end, location, address, pool, `status` (`open` / `full` / `not_open`), `spots_left`, `booking_url` |

## CLI

```bash
uv run perfectmind swims list --date 2026-11-07 --location cornell   # all swim types
uv run perfectmind swims list -d 2026-11-07 -t lane -t endurance_lane  # only lane swims
uv run perfectmind mcp                                               # run the MCP server on stdio
uv run perfectmind version
```

To inspect the server interactively:

```bash
npx @modelcontextprotocol/inspector uv run perfectmind mcp
```

## Configure

Copy `.env.example` to `.env` and set values (all optional):

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LACUNA_LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Logs go to stderr |
| `LACUNA_BASE_URL` | `https://cityofmarkham.perfectmind.com` | PerfectMind tenant root |
| `LACUNA_DROPIN_WIDGET_ID` | `6825ea71-…` | BookMe4 widget for "Drop-In Programs & Activities" |
| `LACUNA_REQUEST_TIMEOUT` | `30` | HTTP timeout in seconds |
| `LACUNA_USER_AGENT` | `perfectmind-claude-plugin/…` | User-Agent sent to the site |

## How it works

The site has no public API. The client calls the same anonymous JSON endpoints that the booking widget uses:

1. `POST /Clients/BookMe4V2/GetCategoriesDataV2` finds the calendars in the drop-in widget and resolves "Swimming" by name.
2. `GET /Clients/BookMe4BookingPagesV2/EventFilterGroupsV2` gets the filter groups: the published date range and the Program values (resolved by name: "Endurance Lane Swim", "Lane Swim" and "Recreational Swim").
3. `POST /Clients/BookMe4BookingPagesV2/ClassesV2` gets sessions, using a date-range filter for the single day plus the selected swim programs. Each session is labelled with a type from its event name. Paging uses `after=<nextKey>`.

Calendar and program IDs are resolved at runtime and never hard-coded. Filter groups are cached for an hour.

## Install for development

```bash
git clone git@github.com:lacuna-core/lacuna_perfectmind_plugin.git
cd lacuna_perfectmind_plugin
uv sync --dev
uv run pre-commit install   # runs ruff + mypy on every commit
```

## Development

### Running tests

```bash
uv run pytest                        # all tests with coverage
uv run pytest tests/cli/             # single directory
uv run pytest -k test_version        # single test
```

### Lint and type-check

```bash
uv run ruff check --fix   # lint + auto-fix
uv run ruff format        # format
uv run mypy               # strict type-check
```

### Project structure

`src/perfectmind/` is layered:

- **`config.py`** — pydantic-settings with `LACUNA_` env prefix
- **`client/`** — `PerfectMindClient` (thin async httpx wrapper over BookMe4 endpoints) and raw pydantic models
- **`service/swims.py`** — `SwimService`: swim lookup by date, location and type, `SwimSession` output model
- **`mcp/server.py`** — MCP server (`mcp` SDK 2.x `MCPServer`) and composition root
- **`cli/app.py`** — Typer CLI; add sub-commands as `cli/<name>.py` and register via `app.add_typer(...)`

Tests replay recorded responses from `tests/fixtures/` through `httpx.MockTransport` (see `tests/conftest.py`). MCP tools are tested in-process with `mcp.client.Client(server)`.

See `CLAUDE.md` for coding conventions.

### Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org):

```
<type>[optional scope]: <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Subject line ≤ 72 chars, lowercase, imperative mood, no trailing period.

## Releases

Releases are published to [GitHub Releases](../../releases). Each tag (`v*.*.*`) triggers a draft release with auto-generated notes via [git-cliff](https://git-cliff.org/).

### Cutting a release

1. Update `version` in `pyproject.toml`, `src/perfectmind/__init__.py` and `.claude-plugin/plugin.json`.
2. Commit: `chore: bump version to x.y.z`
3. Tag: `git tag vx.y.z && git push origin vx.y.z`
4. The Release workflow generates a draft release with notes from git-cliff — review and publish.
