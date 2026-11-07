"""Full mating-face coverage and explicit residual hydraulic leakage evidence."""

from dataclasses import replace
from typing import cast

import cadquery as cq
import pytest

from efficio.examples.gasket_review import full_face_pump_review, pump_gasket_review
from efficio.objects.gaskets import GasketFace, GasketParameters, Opening, OpeningRole
from efficio.objects.gaskets.face import extrude
from efficio.objects.pumps.blind_support import BlindSupportPart
from efficio.objects.pumps.external_gear import GearPumpGeometry


def test_full_face_covers_noses_and_retains_bolt_openings() -> None:
    body, design = full_face_pump_review()
    d, g = body.d, body.d.pump
    assert design.minimum_width == 2
    assert design.rounded_area_loss > 0
    assert design.stop_planes_checked
    face = body.gasket_faces()["cover_seal"]
    assert len(face.openings) == 5
    assert sum(o.role == OpeningRole.BOLT for o in face.openings) == 4
    assert len(design.free.face.innerWires()) == 5
    free = cast(cq.Shape, design.free.shape().workplane().val())
    _, old = pump_gasket_review()
    old_gasket = cast(cq.Shape, old.free.shape().workplane().val())
    for sign in (-1, 1):
        # A real patch on each nose omitted by the earlier capsule gasket.
        probe = cq.Solid.makeBox(
            1, 1, 0.05, cq.Vector(g.centres / 2 - 0.5, sign * 9 - 0.5, g.depth - 0.05)
        )
        assert free.intersect(probe).Volume() == pytest.approx(probe.Volume())
        assert old_gasket.intersect(probe).Volume() < 1e-7
    for k in face.keepouts:
        assert design.clearance_envelope.intersect(k.solid).Volume() < 1e-7
    cover_shape = BlindSupportPart(d, "cover").shape()
    assert cover_shape is not None
    cover = cast(cq.Shape, cover_shape.workplane().val())
    assert design.installed_estimate.intersect(cover).Volume() < 1e-7
    assert design.clearance_envelope.cut(design.recess_envelope).Volume() < 1e-7
    assert d.wall_measurements()["port_roof_to_gasket"] == pytest.approx(2.08)


def test_oval_groove_does_not_connect_to_wet_cavity() -> None:
    body, old = pump_gasket_review()
    cavity = GearPumpGeometry(**vars(body.d.pump)).cavity()
    assert old.recess_envelope.distance(cavity) == pytest.approx(0.7)
    # The old noses had hard contact at the cover plane, not an open gasket gap.
    shape = body.shape()
    assert shape is not None
    solid = cast(cq.Shape, shape.workplane().val())
    for sign in (-1, 1):
        probe = cq.Solid.makeBox(
            1, 1, 0.05, cq.Vector(9.5, sign * 9 - 0.5, body.d.pump.depth - 0.05)
        )
        assert solid.intersect(probe).Volume() == pytest.approx(probe.Volume())


def test_face_gap_remains_connected_and_rotors_clear() -> None:
    body, design = full_face_pump_review()
    g = GearPumpGeometry(**vars(body.d.pump))
    source = body.shape()
    cover_shape = BlindSupportPart(body.d, "cover").shape()
    assert source is not None and cover_shape is not None
    housing = cast(cq.Shape, source.workplane().val())
    cover = cast(cq.Shape, cover_shape.workplane().val())
    gap = g.cavity().intersect(
        cq.Solid.makeBox(
            100,
            100,
            g.face_clearance / 2,
            cq.Vector(-40, -50, g.depth - g.face_clearance / 2),
        )
    )
    assert len(gap.Solids()) == 1 and gap.Volume() > 0
    assert gap.intersect(housing).Volume() < 1e-7
    assert gap.intersect(cover).Volume() < 1e-7
    rotor_shape = g.gear().shape()
    assert rotor_shape is not None
    rotor = cast(cq.Shape, rotor_shape.workplane().val())
    for angle in (0, 30, 60, 90, 180, 270):
        left = rotor.rotate((0, 0, 0), (0, 0, 1), angle).translate(
            (0, 0, g.base + g.face_clearance)
        )
        right = rotor.rotate((0, 0, 0), (0, 0, 1), g.idler_phase(angle)).translate(
            (g.centres, 0, g.base + g.face_clearance)
        )
        for gear in (left, right):
            for fixed in (housing, cover, design.clearance_envelope, gap):
                assert gear.intersect(fixed).Volume() < 1e-7


def test_rolling_width_rejects_disconnected_narrow_waist() -> None:
    outer = (
        cq.Workplane("XY")
        .polyline(
            [
                (-10, -5),
                (-2, -5),
                (-2, -0.4),
                (2, -0.4),
                (2, -5),
                (10, -5),
                (10, 5),
                (2, 5),
                (2, 0.4),
                (-2, 0.4),
                (-2, 5),
                (-10, 5),
            ]
        )
        .close()
        .wire()
        .val()
    )
    assert isinstance(outer, cq.Wire)
    hole = cq.Wire.makeCircle(1, cq.Vector(-6, 0, 0), cq.Vector(0, 0, 1))
    face = cq.Face.makeFromWires(outer, [hole])
    declared = GasketFace(
        face,
        (Opening("wet", face.innerWires()[0], OpeningRole.WET_CAVITY),),
        (),
        cq.Vector(0, 0, 1),
        1,
        "test fixture datum",
    )
    with pytest.raises(ValueError):
        declared.generate(GasketParameters(1.01, 0, 0, round_to_width=True))


def test_recess_depth_requires_port_roof_coordination() -> None:
    body, _ = full_face_pump_review()
    unlowered = replace(body.d, pump=replace(body.d.pump, port_drop=0.3))
    assert unlowered.wall_measurements()["port_roof_to_gasket"] < 2
    with pytest.raises(ValueError, match="generate_gasket"):
        BlindSupportPart(body.d, "gasket", gasket_style="full_face")
