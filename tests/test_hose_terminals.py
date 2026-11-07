"""Terminal connectivity, hose/clamp access and finished-wall checks."""

from dataclasses import replace
from typing import Any

import cadquery as cq
import pytest

from efficio.examples.water_feature_pump import (
    resin_water_profile,
    water_feature_pump,
    water_hose_terminal,
    water_pump_dimensions,
    water_wall_policy,
)
from efficio.objects.connectors import HoseBarb
from efficio.objects.pumps.blind_support import BlindSupportPart
from efficio.objects.pumps.external_gear import GearPumpGeometry


def test_reusable_barb_and_invalid_parameters() -> None:
    d = water_hose_terminal(water_pump_dimensions())
    for dimensions in (d, replace(d, bore_radius=1.5, length=30, barb_starts=(15, 22))):
        shape = HoseBarb(dimensions).shape()
        assert shape is not None
        solid = shape.workplane().val()
        assert isinstance(solid, cq.Shape)
        assert solid.isValid() and len(solid.Solids()) == 1
        assert solid.intersect(HoseBarb(dimensions).bore()).Volume() < 1e-7
    invalid: tuple[dict[str, Any], ...] = (
        {"bore_radius": 4.0},
        {"hose_id": 9.0},
        {"clamp_length": 10.0},
        {"length": 22.0},
    )
    for kwargs in invalid:
        with pytest.raises(ValueError):
            replace(d, **kwargs)


def test_actual_passages_open_through_terminal_and_into_chamber() -> None:
    d = water_pump_dimensions()
    h = water_hose_terminal(d)
    terminal = HoseBarb(h)
    body_object = BlindSupportPart(d, "body", h, 12)
    shape = body_object.shape()
    assert shape is not None
    body = shape.workplane().val()
    assert isinstance(body, cq.Shape)
    g = GearPumpGeometry(**vars(d.pump))
    for sign in (-1, 1):
        bore = body_object.place_terminal(terminal.bore(), sign)
        drilling = g.port_void(sign)
        assert bore.intersect(drilling).Volume() > 1
        connected = bore.fuse(drilling, g.cavity()).clean()
        assert connected.isValid() and len(connected.Solids()) == 1
        assert body.intersect(connected).Volume() < 1e-6
    assert body.isValid() and len(body.Solids()) == 1


def test_hose_clamp_envelopes_clear_case_cover_and_hardware_axes() -> None:
    d = water_pump_dimensions()
    terminal = HoseBarb(water_hose_terminal(d))
    body_object = BlindSupportPart(d, "body", terminal.dimensions, 12)
    parts = water_feature_pump().preview_parts()
    for sign in (-1, 1):
        access = body_object.place_terminal(terminal.access_envelope(), sign)
        terminal_outer = body_object.place_terminal(terminal.envelope(), sign)
        for name, part, _ in parts:
            check = access.cut(terminal_outer) if name == "water_body" else access
            assert check.intersect(part).Volume() < 1e-6, name
        # Conservative straight tool paths above the four case bolt axes.
        for x, y in d.bolt_points:
            tool = cq.Solid.makeCylinder(
                3.5, d.pump.depth + d.pump.cover + 20, cq.Vector(x, y, 0)
            )
            assert access.intersect(tool).Volume() < 1e-6


def test_gasket_roof_budget_and_material_scaled_terminal() -> None:
    d = water_pump_dimensions()
    h = water_hose_terminal(d)
    assert h.finished_wall == 2
    assert d.wall_measurements()["port_roof_to_gasket"] == pytest.approx(2.08)
    old_axis = replace(d, pump=replace(d.pump, port_drop=0))
    assert old_axis.wall_measurements()["port_roof_to_gasket"] == pytest.approx(1.78)
    assert water_hose_terminal(
        water_pump_dimensions(
            replace(
                resin_water_profile(), policy=replace(water_wall_policy(), minimum_mm=3)
            )
        )
    ).finished_wall == pytest.approx(3.0)
