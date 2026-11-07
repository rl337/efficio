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


def test_organic_case_preserves_cavity_joint_and_rotating_parts() -> None:
    d = water_pump_dimensions()
    legacy = replace(d, exterior_offset=0, boss_radius=0, bevel=0)
    for kind in ("gasket", "driver_shaft", "idler_shaft"):
        old, new = solid(legacy, kind), solid(d, kind)
        assert old.cut(new).Volume() + new.cut(old).Volume() < 1e-7
    for kind in ("body", "cover"):
        new, old = solid(d, kind), solid(legacy, kind)
        assert new.Volume() < old.Volume()
        assert new.cut(old).Volume() < 1e-7  # bosses fit inside the previous capsule
        assert new.isValid() and len(new.Solids()) == 1
    g = GearPumpGeometry(**vars(d.pump))
    assert solid(d, "body").intersect(g.cavity()).Volume() < 1e-7


def test_bevels_remove_only_exposed_end_rims() -> None:
    d = water_pump_dimensions()
    plain = replace(d, bevel=0)
    for kind in ("body", "cover"):
        beveled, full = solid(d, kind), solid(plain, kind)
        removed = full.cut(beveled)
        assert removed.Volume() > 0
        assert beveled.cut(full).Volume() < 1e-7
        bounds = removed.BoundingBox()
        if kind == "body":
            assert bounds.zmax == pytest.approx(d.bevel, abs=1e-6)
        else:
            assert bounds.zmin == pytest.approx(
                d.pump.depth + d.pump.cover - d.bevel, abs=1e-6
            )


def test_actual_brep_interface_distances_meet_policy() -> None:
    from efficio.examples.water_feature_pump import water_wall_policy
    from efficio.objects.pumps.blind_support import measured_housing_interfaces

    d = water_pump_dimensions()
    measured = measured_housing_interfaces(d)
    assert measured["bolt_boss_ligament"] == pytest.approx(2.4)
    assert measured["gasket_outer_waist_vertical"] == pytest.approx(2.4252154482)
    water_wall_policy().require({**d.wall_measurements(), **measured})
