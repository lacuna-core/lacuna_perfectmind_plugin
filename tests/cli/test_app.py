import pytest
from typer.testing import CliRunner

from perfectmind.cli.app import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_version() -> None:
    from perfectmind import __version__

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.mark.parametrize("args", [["mcp", "--help"], ["swims", "list", "--help"]])
def test_subcommand_help(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0


def test_swims_lane_rejects_bad_date() -> None:
    result = runner.invoke(app, ["swims", "list", "--date", "not-a-date"])
    assert result.exit_code == 1
