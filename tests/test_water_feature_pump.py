"""Wet-end topology, independent sizing and sampled motion (not hydraulics)."""

from dataclasses import replace
from typing import Any

import cadquery as cq
import pytest

from efficio.examples.water_feature_pump import (
    water_feature_pump,
    water_pump_dimensions,
)
from efficio.objects.pumps.blind_support import BlindSupportPart, cylinder
from efficio.objects.pumps.external_gear import GearPumpGeometry
from efficio.objects.pumps.geometry import BlindSupportDimensions


def solid(d: BlindSupportDimensions, kind: str) -> cq.Shape:
    result = BlindSupportPart(d, kind).shape()
    assert result is not None
    value = result.workplane().val()
    assert isinstance(value, cq.Shape)
    return value


def test_sizes_and_invalid_interfaces() -> None:
    d = water_pump_dimensions()
    assert not d.problems()
    assert d.pump.centres == 20
    changes: list[dict[str, Any]] = [
        dict(seal_depth=9),
        dict(back_web=9),
        dict(gasket_width=5),
        dict(shaft_radius=4),
        dict(end_gap=float("nan")),
    ]
    for change in changes:
        with pytest.raises(ValueError):
            replace(d, **change)


@pytest.mark.parametrize("angle", [0, 4, 8, 11.25, 16, 22.5])
def test_wet_end_solids_and_motion(angle: float) -> None:
    a = water_feature_pump(angle)
    parts = a.preview_parts()
    assert len(parts) == 9
    assert all(s.isValid() and len(s.Solids()) == 1 for _, s, _ in parts)
    for i, (name, shape, _) in enumerate(parts):
        for other_name, other, _ in parts[i + 1 :]:
            assert shape.intersect(other).Volume() < 1e-6, (name, other_name)


def test_blind_bores_single_external_exit_and_gasket() -> None:
    d = water_pump_dimensions()
    g = d.pump
    body, cover, gasket = [solid(d, k) for k in ("body", "cover", "gasket")]
    for x in (0, g.centres):
        probe = cylinder(1, 0.1, d.back_web - 0.1, x=x)
        assert body.intersect(probe).Volume() == pytest.approx(probe.Volume())
    probe = cylinder(1, g.depth + g.cover - 1, g.depth + g.cover - 0.1, x=g.centres)
    assert cover.intersect(probe).Volume() == pytest.approx(probe.Volume())
    driver = cylinder(1, g.depth + 0.1, g.depth + g.cover - 0.1)
    assert cover.intersect(driver).Volume() < 1e-8
    assert body.intersect(gasket).Volume() < 1e-8
    assert cover.intersect(gasket).Volume() < 1e-8


def test_both_ports_reach_chamber_and_alternate_dimensions() -> None:
    d = water_pump_dimensions()
    g = GearPumpGeometry(**vars(d.pump))
    body = solid(d, "body")
    for sign in (-1, 1):
        assert g.port_void(sign).intersect(g.cavity()).Volume() > 1
        assert body.intersect(g.port_void(sign)).Volume() < 1e-7
    changed = replace(d, pump=replace(g, width=10, wall=12), gasket_width=2)
    for kind in ("body", "cover", "gasket", "driver_shaft", "idler_shaft"):
        result = solid(changed, kind)
        assert result.isValid() and len(result.Solids()) == 1
