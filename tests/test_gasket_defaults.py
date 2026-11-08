"""Defaults are caller conveniences, never an inferred installed height."""

from dataclasses import replace
from typing import cast

import cadquery as cq
import pytest

from efficio.examples.gasket_review import (
    full_face_pump_review,
    rectangular_gasket_review,
)
from efficio.objects.gaskets import GasketParameters


def test_defaults_and_legacy_positional_arguments() -> None:
    default = GasketParameters()
    assert default.free_thickness == 2
    assert default.minimum_width == 1
    assert default.resolved_outer_inset == default.resolved_inner_inset == 0.4
    assert not default.problems()
    legacy = GasketParameters(0.31, 1, 2, 1.1, 1.2, False)
    assert (
        legacy.free_thickness,
        legacy.resolved_outer_inset,
        legacy.resolved_inner_inset,
        legacy.spread_margin,
        legacy.minimum_width,
    ) == (0.31, 1, 2, 1.1, 1.2)


def test_common_inset_and_independent_overrides() -> None:
    p = GasketParameters(inset=0.6, inner_inset=0)
    assert p.resolved_outer_inset == 0.6 and p.resolved_inner_inset == 0
    changed = replace(p, inset=0.8)
    assert changed.resolved_outer_inset == 0.8 and changed.resolved_inner_inset == 0
    p = GasketParameters(inset=0.6, outer_inset=0.2)
    assert p.resolved_outer_inset == 0.2 and p.resolved_inner_inset == 0.6


@pytest.mark.parametrize(
    "parameters",
    [
        GasketParameters(inset=-1),
        GasketParameters(inset=float("nan")),
        GasketParameters(inner_inset=-0.1),
        GasketParameters(outer_inset=float("inf")),
        GasketParameters(minimum_width=0),
        GasketParameters(free_thickness=0),
    ],
)
def test_invalid_defaults_overrides_are_reported(parameters: GasketParameters) -> None:
    assert parameters.problems()


def test_defaults_build_only_with_deliberate_compatible_height() -> None:
    _, face, _ = rectangular_gasket_review()
    with pytest.raises(ValueError, match="overfills"):
        face.generate(GasketParameters())
    compatible = replace(
        face,
        closed_height=1.98,
        closure_description="Explicit test fixture height; no material qualification",
    )
    result = compatible.generate(GasketParameters())
    assert result.free.thickness == 2
    assert cast(cq.Shape, result.free.shape().workplane().val()).isValid()
    assert result.minimum_width == pytest.approx(3.7)
    compatible.generate(GasketParameters(minimum_width=3.7))
    with pytest.raises(ValueError, match="below minimum"):
        compatible.generate(GasketParameters(minimum_width=3.70001))
    with pytest.raises(ValueError, match="hard-stop"):
        replace(compatible, closed_height=0).generate(GasketParameters())
    with pytest.raises(ValueError, match="hard-stop"):
        replace(compatible, closure_description="").generate(GasketParameters())
    assert face.closed_height == 0.3


def test_pump_keeps_explicit_thickness_and_rejects_two_mm_default() -> None:
    body, design = full_face_pump_review()
    assert design.free.thickness == 1.05
    face = body.gasket_faces()["cover_seal"]
    assert face.closed_height == 1
    with pytest.raises(ValueError, match="overfills"):
        face.generate(GasketParameters(round_to_width=True))
    explicit = face.generate(
        GasketParameters(free_thickness=1.05, minimum_width=2, round_to_width=True)
    )
    assert explicit.free.face.Area() == pytest.approx(design.free.face.Area())
    assert explicit.installed_estimate.Volume() == pytest.approx(
        design.installed_estimate.Volume()
    )
