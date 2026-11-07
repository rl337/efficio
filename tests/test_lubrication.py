"""Geometric passage continuity, interfaces and motion; not a fluid qualification."""

from dataclasses import replace
from typing import Any

import cadquery as cq
import pytest

from efficio.examples.lubricated_engine import (
    lubricated_engine_assembly,
    lubrication_geometry,
)
from efficio.examples.resin_engine import resin_engine_assembly
from efficio.objects.assembly import Assembly
from efficio.objects.fluids import Point3, TubeNetwork
from efficio.objects.powertrain.engine.lubrication import LubricationSump


@pytest.fixture(scope="module")
def assembly() -> Assembly:
    return lubricated_engine_assembly()


def test_valid_solids_bom_and_original_parts(assembly: Assembly) -> None:
    assert all(
        p.solid.isValid() and len(p.solid.Solids()) == 1
        for p in assembly.all_instances()
    )
    quantities = assembly.quantities()
    assert (
        quantities["oil_pickup"]
        == quantities["oil_supply"]
        == quantities["resin_oil_pan"]
        == 1
    )
    assert quantities["resin_liner"] == 4
    assert len([r for r in assembly.bom_totals() if r["item"] == "oil_supply"]) == 1
    original = resin_engine_assembly()
    for p in original.all_instances():
        if p.label == "resin_oil_pan":
            continue
        assert assembly.instance(p.label).solid.Volume() == pytest.approx(
            p.solid.Volume(), rel=1e-9
        )
    assert assembly.instance("resin_oil_pan").solid.BoundingBox().zmax == pytest.approx(
        lubrication_geometry().housing.liner_bottom
    )


def test_connected_bores_and_open_endpoints(assembly: Assembly) -> None:
    g = lubrication_geometry()
    assert g.problems() == []
    for name, network in [("oil_pickup", g.pickup()), ("oil_supply", g.supply())]:
        bore = network.bore_solid()
        assert bore.isValid() and len(bore.Solids()) == 1
        tube = assembly.instance(name).solid
        assert tube.intersect(bore).Volume() < 1e-6
        for path in network.paths:
            for point in path:
                probe = cq.Solid.makeSphere(
                    g.bore_radius / 3, cq.Vector(*point), angleDegrees1=-90
                )
                assert bore.intersect(probe).Volume() > 0.4 * probe.Volume()
                assert tube.intersect(probe).Volume() < 1e-6
    # External suction and pressure ports remain separate: no pump is invented.
    assert g.pickup().bore_solid().intersect(g.supply().bore_solid()).Volume() < 1e-6


def test_pickup_and_outlet_targets() -> None:
    g = lubrication_geometry()
    e = g.housing.engine
    assert g.pickup_path()[0][2] - (g.bottom + g.housing.shell) == pytest.approx(
        g.pickup_floor_gap
    )
    paths = g.supply_paths()
    for start, end in paths[2 : 2 + e.cylinders]:
        # Extrapolated outlet centerline enters the bore at its lower edge.
        t = (g.housing.liner_bottom - end[2]) / (end[2] - start[2])
        x = end[0] + t * (end[0] - start[0])
        assert abs(x) < e.bore / 2
    assert paths[-2][-1][1] == pytest.approx(e.end_wall + g.bearing_face_gap)
    assert paths[-1][-1][1] == pytest.approx(
        e.block_length - e.end_wall - g.bearing_face_gap
    )


@pytest.mark.parametrize("angle", [0, 45, 90, 135, 180, 225, 270, 315])
def test_motion_clearance(assembly: Assembly, angle: int) -> None:
    # Reuse stationary hardware; generate the existing mechanism at each pose.
    moving = resin_engine_assembly(float(angle))
    probe = Assembly("motion check")
    probe.instances = [
        p for p in assembly.all_instances() if p.label.startswith(("resin_", "oil_"))
    ]
    probe.instances += [
        p for p in moving.all_instances() if not p.label.startswith("resin_")
    ]
    assert probe.interferences() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"gallery_inset": 0.1},
        {"bore_radius": -1.0},
        {"nozzle_below_liner": 1.0},
        {"gallery_end_offset": 100.0},
    ],
)
def test_invalid_oil_geometry(changes: dict[str, Any]) -> None:
    g = replace(lubrication_geometry(), **changes)
    assert g.problems()
    with pytest.raises(ValueError):
        LubricationSump(g).shape()


def test_generic_tube_network_supports_a_different_size() -> None:
    tube = TubeNetwork(
        [[(0, 0, 0), (0, 0, 10), (10, 0, 10)], [(0, 0, 5), (0, 10, 5)]], 0.8, 0.6
    )
    shape = tube.shape()
    assert shape is not None
    solid = shape.workplane().val()
    assert isinstance(solid, cq.Shape)
    assert solid.isValid() and len(solid.Solids()) == 1
    assert len(tube.bore_solid().Solids()) == 1
    invalid: list[tuple[list[list[Point3]], float, float]] = [
        ([], 1, 1),
        ([[(0, 0, 0)]], 1, 1),
        ([[(0, 0, 0), (0, 0, 0)]], 1, 1),
        ([[(0, 0, 0), (1, 0, 0)]], 0, 1),
    ]
    for paths, r, w in invalid:
        with pytest.raises(ValueError):
            TubeNetwork(paths, r, w)
