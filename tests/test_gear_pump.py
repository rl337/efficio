"""Geometry and connectivity checks, deliberately not hydraulic qualification."""

from dataclasses import replace
from typing import Any, cast

import cadquery as cq
import pytest

from efficio.examples.lubricated_engine import (
    lubricated_engine_assembly,
    lubrication_geometry,
)
from efficio.examples.pumped_engine import (
    external_lines,
    filter_geometry,
    pump_drive_phase,
    pump_geometry,
    pump_point,
    pumped_engine_assembly,
)
from efficio.objects.assembly import Assembly
from efficio.objects.profiles import cylinder
from efficio.objects.pumps.external_gear import GearPumpGeometry, gear_pump_assembly


@pytest.fixture(scope="module")
def pump() -> Assembly:
    return gear_pump_assembly(pump_geometry())


@pytest.fixture(scope="module")
def engine() -> Assembly:
    return pumped_engine_assembly()


def test_pump_valid_and_reusable(pump: Assembly) -> None:
    other = gear_pump_assembly(GearPumpGeometry(module=1.25, teeth=16, width=8))
    for a in (pump, other):
        assert all(
            p.solid.isValid() and len(p.solid.Solids()) == 1 for p in a.all_instances()
        )
        assert a.interferences() == []
        assert a.quantities()["pump_rotor"] == 2
        assert a.quantities()["pump_shaft_collar"] == 4


@pytest.mark.parametrize("angle", range(0, 30, 3))
def test_rotor_mesh_over_one_tooth_pitch(angle: int) -> None:
    assert gear_pump_assembly(pump_geometry(), angle).interferences() == []


def test_port_chambers_are_open_at_multiple_phases() -> None:
    g = pump_geometry()
    for angle in (0, 7.5, 15, 22.5):
        a = gear_pump_assembly(g, angle)
        free = g.cavity().fuse(g.port_void(1), g.port_void(-1))
        for p in a.all_instances():
            free = free.cut(p.solid)
        assert free.isValid()
        # Positive face/tip gaps connect the domain, also demonstrating leakage.
        # This is NOT evidence that the rotors establish pressure or net flow.
        assert len(free.Solids()) == 1
        for sign in (-1, 1):
            tip = cq.Solid.makeSphere(
                g.port_radius / 2, cq.Vector(*g.port(sign)), angleDegrees1=-90
            )
            assert free.intersect(tip).Volume() > 0.45 * tip.Volume()
            chamber = cq.Solid.makeSphere(
                0.5,
                cq.Vector(g.centres / 2, sign * 3.5, g.base + g.width / 2),
                angleDegrees1=-90,
            )
            assert free.intersect(chamber).Volume() > 0


def test_engine_parts_mount_bom_and_clearance(engine: Assembly) -> None:
    assert all(
        p.solid.isValid() and len(p.solid.Solids()) == 1 for p in engine.all_instances()
    )
    assert engine.interferences() == []
    assert engine.quantities()["pump_rotor"] == 2
    assert engine.quantities()["resin_liner"] == 4
    original = lubricated_engine_assembly()
    for p in original.all_instances():
        new = engine.instance(p.label).solid
        if p.label == "resin_front_support":
            assert new.Volume() < p.solid.Volume()
            assert new.cut(p.solid).Volume() < 1e-6
        else:
            assert new.cut(p.solid).Volume() < 1e-6
            assert p.solid.cut(new).Volume() < 1e-6
    for name in ("pump_crank_gear", "pump_drive_gear"):
        b = engine.instance(name).solid.BoundingBox()
        assert b.ymin == pytest.approx(-7.5)
        assert b.ymax == pytest.approx(-2.5)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_integrated_drive_motion(angle: int) -> None:
    assert pumped_engine_assembly(angle).interferences() == []


def test_pipe_connections_and_filter_openings(engine: Assembly) -> None:
    g = lubrication_geometry()
    networks = external_lines()
    inlet = networks["pump_suction_line"].bore_solid().fuse(g.pickup().bore_solid())
    assert len(inlet.Solids()) == 1
    f = filter_geometry()
    # Actual fluid space inside the assembled strainer, with perforated insert.
    chamber = cast(
        cq.Shape, cylinder(f.radius - f.wall, f.end_wall, f.length - f.end_wall).val()
    ).fuse(cast(cq.Shape, cylinder(f.port_radius, 0, f.length).val()))
    chamber = chamber.rotate((0, 0, 0), (1, 0, 0), -90).translate((-70, 20, 16))
    chamber = chamber.cut(engine.instance("oil_filter_screen").solid)
    assert len(chamber.Solids()) == 1
    pressure = (
        networks["pump_pressure_line"]
        .bore_solid()
        .fuse(
            chamber,
            networks["pump_delivery_line"].bore_solid(),
            g.supply().bore_solid(),
        )
    )
    assert len(pressure.Solids()) == 1
    for fluid in (pressure, inlet):
        # Pickup screen is intentionally immersed; its apertures stay open.
        for p in engine.all_instances():
            if p.label != "pickup_screen":
                assert p.solid.intersect(fluid).Volume() < 1e-5, p.label
    assert len(inlet.cut(engine.instance("pickup_screen").solid).Solids()) == 1
    for sign, fluid in [(1, inlet), (-1, pressure)]:
        endpoint = cq.Solid.makeSphere(
            0.5, cq.Vector(*pump_point(pump_geometry().port(sign))), angleDegrees1=-90
        )
        assert fluid.intersect(endpoint).Volume() > 0.45 * endpoint.Volume()
    # A relief valve has NOT been modeled across these deliberately open ports.
    assert inlet.intersect(pressure).Volume() < 1e-6


@pytest.mark.parametrize(
    "changes",
    [
        {"module": -1},
        {"teeth": 4},
        {"face_clearance": 2},
        {"shaft_diameter": 20},
        {"seal_pocket_depth": 5},
        {"wall": 1},
    ],
)
def test_invalid_parameters(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(pump_geometry(), **changes)


def test_continuous_shaft_phase_not_tooth_equivalent_wrapping() -> None:
    g = pump_geometry()
    assert g.problems() == []
    for angle in (0, 19.9, 20.1, 90, 359, 720):
        assert pump_drive_phase(angle + 1) - pump_drive_phase(angle) == pytest.approx(
            -18 / 22
        )
        assert g.idler_phase(angle + 1) - g.idler_phase(angle) == pytest.approx(-1)
    assert pump_drive_phase(360) - pump_drive_phase(0) == pytest.approx(-360 * 9 / 11)


def test_round_seal_lands_and_retention(pump: Assembly) -> None:
    g = pump_geometry()
    shaft = pump.instance("pump_driver_shaft").solid
    # A full round section exists at both exterior seal reservations; no D-flat
    # leakage channel crosses a nominal round lip-seal location.
    for z in (0.25, g.depth + g.cover - 0.25):
        disc = cq.Solid.makeCylinder(
            g.shaft_diameter / 2 - 0.051, 0.1, cq.Vector(0, 0, z)
        )
        assert disc.cut(shaft).Volume() < 1e-6
    assert pump.quantities()["pump_rotor_pin"] == 2
    assert g.collar_radius > g.seal_pocket_radius
    assert g.collar_gap < g.face_clearance
