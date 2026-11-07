"""Interfaces and honest geometry boundaries for the resin teaching assembly."""

import math
from dataclasses import replace
from typing import Any

import cadquery as cq
import pytest

from efficio.examples.drivetrain import add_engine
from efficio.examples.resin_engine import resin_engine_assembly, resin_engine_geometry
from efficio.inspection import inspect_parts
from efficio.objects.assembly import Assembly
from efficio.objects.fits import Process
from efficio.objects.powertrain.engine import EngineBlockHalf
from efficio.objects.powertrain.engine.resin import (
    ResinEngineHousingPart,
    ResinHousingPart,
)
from efficio.objects.powertrain.layout import DrivetrainLayout
from efficio.objects.profiles import box, x_cylinder


@pytest.fixture(scope="module")
def assembly() -> Assembly:
    return resin_engine_assembly()


def test_separate_valid_parts_and_single_bom_ownership(assembly: Assembly) -> None:
    assert all(
        p.solid.isValid() and len(p.solid.Solids()) == 1
        for p in assembly.all_instances()
    )
    assert assembly.quantities()["resin_liner"] == 4
    assert assembly.quantities()["piston"] == 4
    assert not any(p.label.startswith("engine_mount") for p in assembly.all_instances())
    hardware = [h for a in assembly.walk() for h in a.hardware]
    assert len(hardware) == 1 and hardware[0].quantity == 2
    assert hardware[0].notes == "Crank mains in block end walls"
    assert assembly.all_parts()["resin_liner"].processes == (Process.RESIN_CAST,)
    assert (
        len(
            [
                r
                for r in assembly.bom_totals()
                if r["item"] == "resin_liner" and r["quantity"] == "4"
            ]
        )
        == 1
    )


def test_liner_has_continuous_full_circumference(assembly: Assembly) -> None:
    g = resin_engine_geometry()
    e = g.engine
    r = g.liner_radius
    expected = math.pi * (r * r - (e.bore / 2) ** 2) * (e.deck_height - g.liner_bottom)
    expected += math.pi * ((r + g.flange_width) ** 2 - r * r) * g.flange_height
    for i in range(e.cylinders):
        assert assembly.instance(f"resin_liner_{i}").solid.Volume() == pytest.approx(
            expected, rel=1e-8
        )
    assert (
        e.rod_length - e.crank_throw - (e.piston_height - e.piston_compression_height)
        >= g.liner_bottom
    )


def test_existing_mechanical_geometry_preserved(assembly: Assembly) -> None:
    original = Assembly("original")
    add_engine(original, DrivetrainLayout(engine=resin_engine_geometry().engine), 30)
    for p in assembly.all_instances():
        if p.label.startswith("resin_"):
            continue
        before = original.instance(p.label).solid
        assert p.solid.Volume() == pytest.approx(before.Volume(), rel=1e-9)
        a, b = p.solid.BoundingBox(), before.BoundingBox()
        assert (a.xmin, a.ymin, a.zmin, a.xmax, a.ymax, a.zmax) == pytest.approx(
            (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax), abs=1e-7
        )


def test_bearing_end_seats_preserve_original_material(assembly: Assembly) -> None:
    g = resin_engine_geometry()
    e = g.engine
    hw = e.block_half_width
    for upper in (True, False):
        shape = EngineBlockHalf(e, upper).shape()
        assert shape is not None
        original = shape.workplane().val()
        assert isinstance(original, cq.Shape)
        for name, y0, y1 in [
            ("front", 0, e.end_wall),
            ("rear", e.block_length - e.end_wall, e.block_length),
        ]:
            region = box(
                -hw - 1,
                hw + 1,
                y0,
                y1,
                0 if upper else -hw - 1,
                g.jacket_top if upper else 0,
            ).val()
            assert isinstance(region, cq.Shape)
            actual = assembly.instance(
                f"resin_{name}_support" if upper else "resin_bearing_frame"
            ).solid
            assert actual.intersect(region).Volume() == pytest.approx(
                original.intersect(region).Volume(), abs=1e-6
            )


def test_real_ports_and_empty_cavities(assembly: Assembly) -> None:
    g = resin_engine_geometry()
    e = g.engine
    hw = e.block_half_width
    jacket = assembly.instance("resin_jacket").solid
    y = e.end_wall + g.shell + g.port_radius + 1
    z = g.liner_bottom + g.shell + 2 * g.port_radius
    probe = x_cylinder(g.port_radius * 0.9, -hw - 1, -hw + g.shell + 1, y, z).val()
    assert isinstance(probe, cq.Shape)
    assert jacket.intersect(probe).Volume() < 1e-7
    pan = assembly.instance("resin_oil_pan").solid
    probe = x_cylinder(
        g.port_radius * 0.9,
        -hw - 1,
        -hw + g.shell + 1,
        e.end_wall + g.shell + 2 * g.port_radius,
        -hw - g.pan_drop + g.shell + g.port_radius,
    ).val()
    assert isinstance(probe, cq.Shape)
    assert pan.intersect(probe).Volume() < 1e-7
    for solid, low, high in [
        (jacket, g.liner_bottom + g.shell, g.jacket_top),
        (pan, -hw - g.pan_drop + g.shell, -g.frame_rail),
    ]:
        cavity = box(
            -hw + g.shell,
            hw - g.shell,
            e.end_wall + g.shell,
            e.block_length - e.end_wall - g.shell,
            low,
            high,
        ).val()
        assert isinstance(cavity, cq.Shape)
        assert solid.intersect(cavity).Volume() < 1e-6


@pytest.mark.parametrize("angle", [0.0, 90.0, 180.0, 270.0])
def test_resin_assembly_motion_clearance(angle: float) -> None:
    assert resin_engine_assembly(angle).interferences() == []


def test_display_cut_does_not_cut_manufactured_parts(assembly: Assembly) -> None:
    parts = assembly.find("Housing").preview_parts()
    before = [p[1].Volume() for p in parts]
    cut = inspect_parts(parts, axis="X", position=0)
    assert sum(p[1].Volume() for p in cut) < sum(before)
    assert [p[1].Volume() for p in parts] == before


@pytest.mark.parametrize(
    "changes",
    [
        {"liner_wall": 8.0},
        {"shell": 15.0},
        {"flange_height": 5.0},
        {"clearance": -1.0},
        {"port_radius": float("nan")},
        {"port_radius": 20.0},
    ],
)
def test_invalid_interfaces_rejected(changes: dict[str, Any]) -> None:
    g = replace(resin_engine_geometry(), **changes)
    assert g.problems()
    with pytest.raises(ValueError):
        ResinEngineHousingPart(g, ResinHousingPart.LINER).shape()


def test_single_cylinder_variant_and_reject_windowed_base() -> None:
    g = resin_engine_geometry()
    g.engine = replace(g.engine, cylinders=1)
    assert g.problems() == []
    for kind in ResinHousingPart:
        shape = ResinEngineHousingPart(g, kind).shape()
        assert shape is not None
        solid = shape.workplane().val()
        assert isinstance(solid, cq.Shape)
        assert solid.isValid() and len(solid.Solids()) == 1
    g.engine.windowed_block = True
    assert "resin assembly requires continuous, unwindowed cylinders" in g.problems()
