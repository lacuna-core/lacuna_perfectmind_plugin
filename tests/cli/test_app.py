from typer.testing import CliRunner

from perfectmind.cli.app import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_version() -> None:
    from perfectmind import __version__

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert __version__ in result.output
