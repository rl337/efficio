"""Regression coverage for entry points recovered from the original report branch."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from efficio import inspection


def test_inspection_cli_forwards_output_directory(tmp_path: Path) -> None:
    with patch.object(
        inspection, "generate_example_inspection_pdfs", return_value=[]
    ) as generate:
        assert inspection.main(["--output-dir", str(tmp_path)]) == 0
    generate.assert_called_once_with(str(tmp_path))


def test_preview_batch_continues_after_render_failure(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "generate_previews.py"
    spec = importlib.util.spec_from_file_location("generate_previews", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="shape.*returned None"):
        module.save("missing", None)
    tooling = MagicMock()
    tooling.cottle_sections.return_value = []
    output = tmp_path / "new-directory"
    with (
        patch.object(module, "OUT_DIR", str(output)),
        patch.object(module, "resin_spherical_gear_tooling", return_value=tooling),
        patch.object(module, "plaster_triangular_flask_tooling", return_value=tooling),
        patch.object(module, "SphericalGear"),
        patch.object(module, "RectangularGear"),
        patch.object(module, "TrapezoidalGear"),
        patch.object(module, "TriangularFlaskVase"),
        patch.object(
            module, "save", side_effect=[RuntimeError("render failed")] + [None] * 6
        ) as save,
        patch.object(
            module, "generate_example_inspection_pdfs", return_value=[]
        ) as pdfs,
    ):
        assert module.main() == 1
        assert output.is_dir()
        assert save.call_count == 7
        pdfs.assert_called_once_with(str(output))
