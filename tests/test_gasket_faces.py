"""Face declarations, exact limited-family band checks and failure paths."""

from dataclasses import replace
from typing import cast

import cadquery as cq
import pytest

from efficio.examples.water_feature_pump import water_pump_dimensions
from efficio.objects.base import EfficioObject
from efficio.objects.gaskets import (
    GasketFace,
    GasketParameters,
    KeepOut,
    Opening,
    OpeningRole,
)
from efficio.objects.gaskets.width import measure_band_width
from efficio.objects.pumps.blind_support import BlindSupportPart


def flange() -> GasketFace:
    solid = (
        cq.Workplane("XY")
        .box(40, 30, 3)
        .faces(">Z")
        .workplane()
        .hole(12)
        .faces(">Z")
        .workplane()
        .pushPoints([(-14, 0), (14, 0)])
        .hole(3)
        .val()
    )
    assert isinstance(solid, cq.Shape)
    face = max(
        (f for f in solid.Faces() if f.geomType() == "PLANE"),
        key=lambda f: f.Center().z,
    )
    openings = tuple(
        Opening(
            f"hole_{i}",
            w,
            (
                OpeningRole.WET_CAVITY
                if cq.Face.makeFromWires(w).Area() > 50
                else OpeningRole.BOLT
            ),
        )
        for i, w in enumerate(face.innerWires())
    )
    return GasketFace(
        face,
        openings,
        (),
        cq.Vector(0, 0, 1),
        0.3,
        "Example rigid closure datum: 0.3 mm above plate face; fixture not generated",
    )


def test_pump_face_generated_parts_volume_and_keepouts() -> None:
    body = BlindSupportPart(water_pump_dimensions(), "body")
    declared = body.gasket_faces()["cover_seal"]
    result = body.generate_gasket("cover_seal", GasketParameters(0.36, 0.2, 0.2))
    free = cast(cq.Shape, result.free.shape().workplane().val())
    assert free.isValid() and result.installed_estimate.isValid()
    assert result.minimum_width == pytest.approx(1.1)
    assert result.squeeze_fraction == pytest.approx(1 / 6)
    assert free.Volume() == pytest.approx(result.installed_estimate.Volume(), rel=1e-7)
    assert result.gland_fill_fraction < 1
    for k in declared.keepouts:
        assert result.clearance_envelope.intersect(k.solid).Volume() < 1e-7
    assert result.clearance_envelope.cut(result.recess_envelope).Volume() < 1e-7
    assert free.BoundingBox().zmax == pytest.approx(
        water_pump_dimensions().pump.depth + 0.06
    )


def test_other_flange_retains_all_openings_and_changes_parameters() -> None:
    f = flange()
    result = f.generate(GasketParameters(0.31, 1, 1, 1.1))
    assert len(result.free.face.innerWires()) == 3
    assert result.minimum_width >= 1
    assert cast(cq.Shape, result.free.shape().workplane().val()).isValid()
    assert len(f.openings) == 3
    assert result.free.thickness != 0.36


def test_explicit_openings_required_no_guessing() -> None:
    f = flange()
    for openings in ((), f.openings[:-1], (f.openings[0],) * 3):
        with pytest.raises(ValueError, match="identified exactly once"):
            replace(f, openings=openings).generate(GasketParameters(0.31, 1, 1))
    with pytest.raises(ValueError, match="Unknown gasket"):
        EfficioObject().generate_gasket("unknown", GasketParameters(0.36, 0.2, 0.2))


def test_minimum_width_boundary_and_narrow_band() -> None:
    body = BlindSupportPart(water_pump_dimensions(), "body")
    # Actual post-inset width is 1 mm, not the original 1.5 mm recess.
    result = body.generate_gasket("cover_seal", GasketParameters(0.31, 0.25, 0.25))
    assert result.minimum_width == pytest.approx(1)
    with pytest.raises(ValueError, match="below minimum"):
        body.generate_gasket("cover_seal", GasketParameters(0.31, 0.251, 0.25))
    with pytest.raises(ValueError, match="below minimum"):
        body.generate_gasket(
            "cover_seal", GasketParameters(0.31, 0.2, 0.2, minimum_width=1.2)
        )


def test_narrow_waist_fails_closed() -> None:
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
    hole = cq.Wire.makeCircle(1, cq.Vector(-6, 0, 0), cq.Vector(0, 0, 1))
    assert isinstance(outer, cq.Wire)
    face = cq.Face.makeFromWires(outer, [hole])
    with pytest.raises(ValueError, match="cannot certify"):
        measure_band_width(face)


def test_keepout_overfill_and_bad_inputs() -> None:
    f = flange()
    blocker = cq.Solid.makeBox(100, 100, 10, cq.Vector(-50, -50, -1))
    with pytest.raises(ValueError, match="keep-out"):
        replace(f, keepouts=(KeepOut("moving part", blocker),)).generate(
            GasketParameters(0.31, 1, 1)
        )
    with pytest.raises(ValueError, match="overfills"):
        f.generate(GasketParameters(5, 0.1, 0.1))
    with pytest.raises(ValueError, match="stand proud"):
        f.generate(GasketParameters(0.2, 1, 1))
    with pytest.raises(ValueError, match="normal"):
        replace(f, normal=cq.Vector(1, 0, 0)).generate(GasketParameters(0.31, 1, 1))
    with pytest.raises(ValueError, match="hard-stop"):
        replace(f, closure_description="").generate(GasketParameters(0.31, 1, 1))
    with pytest.raises(ValueError):
        f.generate(GasketParameters(float("nan"), 1, 1))


def test_wider_pump_review_preserves_chamber_and_walls() -> None:
    from efficio.examples.gasket_review import pump_gasket_review
    from efficio.examples.water_feature_pump import water_wall_policy
    from efficio.objects.pumps.external_gear import GearPumpGeometry

    body, result = pump_gasket_review()
    d = body.d
    assert result.minimum_width == pytest.approx(2.6)
    water_wall_policy().require(d.wall_measurements())
    assert (
        d.pump.wall / 2 - d.pump.bolt_radius - d.gasket_inset - d.gasket_width
        == pytest.approx(2.65)
    )
    old = GearPumpGeometry(**vars(water_pump_dimensions().pump)).cavity()
    new = GearPumpGeometry(**vars(d.pump)).cavity()
    assert old.cut(new).Volume() + new.cut(old).Volume() < 1e-7
    cover_shape = BlindSupportPart(d, "cover").shape()
    assert cover_shape is not None
    cover = cast(cq.Shape, cover_shape.workplane().val())
    assert cover.intersect(result.installed_estimate).Volume() < 1e-7


def test_rotated_flange_and_nonplanar_face() -> None:
    f = flange()
    moved = f.face.rotate((0, 0, 0), (1, 0, 0), 35)
    openings = tuple(
        Opening(f"hole_{i}", w, OpeningRole.OTHER)
        for i, w in enumerate(moved.innerWires())
    )
    normal = moved.normalAt()
    result = replace(f, face=moved, openings=openings, normal=normal).generate(
        GasketParameters(0.31, 1, 1)
    )
    assert cast(cq.Shape, result.free.shape().workplane().val()).isValid()
    cylinder = cq.Solid.makeCylinder(5, 4)
    curved = next(face for face in cylinder.Faces() if face.geomType() == "CYLINDER")
    with pytest.raises(ValueError, match="planar"):
        replace(f, face=curved).generate(GasketParameters(0.31, 1, 1))


def test_bolt_hole_ligament_is_measured_after_insets() -> None:
    f = flange()
    result = f.generate(GasketParameters(0.301, 1, 2.4, 1))
    assert result.minimum_width == pytest.approx(1.1)
    with pytest.raises(ValueError, match="below minimum"):
        f.generate(GasketParameters(0.301, 1, 2.51, 1))


def test_offset_topology_and_margin_escape_fail() -> None:
    f = flange()
    with pytest.raises(ValueError):
        f.generate(GasketParameters(0.31, 20, 1))
    body = BlindSupportPart(water_pump_dimensions(), "body")
    with pytest.raises(ValueError, match="escapes recess"):
        body.generate_gasket("cover_seal", GasketParameters(0.36, 0.2, 0.2, 5))


def test_declared_stop_planes_are_checked_separately() -> None:
    body = BlindSupportPart(water_pump_dimensions(), "body")
    face = body.gasket_faces()["cover_seal"]
    result = face.generate(GasketParameters(0.36, 0.2, 0.2))
    assert result.stop_planes_checked
    wrong = face.stop_faces[0].translate((0, 0, 1))
    with pytest.raises(ValueError, match="hard-stop face"):
        replace(face, stop_faces=(wrong,)).generate(GasketParameters(0.36, 0.2, 0.2))
    assert not flange().generate(GasketParameters(0.31, 1, 1)).stop_planes_checked
