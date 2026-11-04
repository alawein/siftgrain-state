import pytest

from siftgrain_state.cli import main


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "packet" in capsys.readouterr().out
