"""Execute every reference notebook in replay mode; fail on any error or on 'NaN'/'undefined' in outputs.

Offline by construction: nbhelpers.setup() forces TI_MODE=replay, and a cache miss raises instead of calling the network.
"""
import os
import re
from pathlib import Path

import nbformat
import pytest

nbclient = pytest.importorskip("nbclient")

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("0*.ipynb"))
BAD = re.compile(r"(?<![A-Za-z])(NaN|undefined)(?![A-Za-z])")


def test_seven_notebooks_exist():
    assert len(NOTEBOOKS) == 7


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_runs_in_replay_mode(path, monkeypatch):
    monkeypatch.setenv("TI_MODE", "replay")
    monkeypatch.setenv("JUPYTER_CONFIG_DIR", str(ROOT / "notebooks" / ".no_jupyter_config"))
    nb = nbformat.read(path, as_version=4)
    nbclient.NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}}).execute()
    for i, cell in enumerate(nb.cells):
        for out in cell.get("outputs", []) if cell.cell_type == "code" else []:
            assert out.output_type != "error"
            blob = out.get("text", "") + "".join(str(v) for k, v in out.get("data", {}).items() if k.startswith("text/"))
            assert not BAD.search(blob), f"{path.name} cell {i}: NaN/undefined in output"
