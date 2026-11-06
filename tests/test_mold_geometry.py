"""Intersection tests, not merely valid-solid tests, for mold geometry."""

import cadquery as cq
import pytest

from efficio.examples.mold_tooling import (
    plaster_triangular_flask_tooling,
    resin_spherical_gear_tooling,
)
from efficio.measures import Millimeter
from efficio.objects.molds import CottlePurpose, MoldFeatures, MoldPolarity, MoldTooling
from efficio.objects.primitives import Box
from efficio.objects.vessels import TriangularFlaskVase


def volume(wp: cq.Workplane) -> float:
    return sum(s.Volume() for s in wp.solids().vals() if isinstance(s, cq.Shape))


@pytest.mark.parametrize("purpose", list(CottlePurpose))
def test_cottle_has_no_silicone_or_half_collisions(purpose: CottlePurpose) -> None:
    tooling = MoldTooling(
        Box(Millimeter(30), Millimeter(26), Millimeter(20)),
        MoldPolarity.NEGATIVE,
        purpose=purpose,
    )
    silicone = tooling.silicone_shape().workplane()
    a, b = [section.geometry.workplane() for section in tooling.cottle_sections()]
    for shell in (a, b):
        assert len(shell.solids().vals()) == 1
        assert volume(shell.intersect(silicone)) < 1e-6
    assert volume(a.intersect(b)) < 1e-6


def test_ports_connect_master_to_roof_and_share_axes() -> None:
    tooling = MoldTooling(
        Box(Millimeter(30), Millimeter(26), Millimeter(20)), MoldPolarity.NEGATIVE
    )
    master, bounds = tooling._master_shape_and_bounds()
    silicone = tooling.silicone_shape().workplane()
    roof_top = tooling._cottle_dimensions()[2] / 2
    shells = [s.geometry.workplane() for s in tooling.cottle_sections()]
    for x, y, radius in tooling._pour_ports(bounds):
        probe = cq.Workplane("XY").circle(radius * 0.99).extrude(roof_top - bounds[2])
        probe = probe.translate((x, y, bounds[2]))
        assert volume(probe.intersect(master.workplane())) > 1
        assert volume(probe.intersect(silicone)) < 1e-6
        assert all(volume(probe.intersect(shell)) < 1e-6 for shell in shells)


def test_fastener_cutter_has_shank_head_and_hex_nut_seats() -> None:
    tooling = plaster_triangular_flask_tooling()
    cutter = tooling._fastener_cutter(40).workplane()

    # Slices prove the central hole is shank-sized, not a full boss cylinder.
    def slice_area(z: float) -> float:
        slab = cq.Workplane("XY").box(20, 20, 0.1).translate((0, 0, z))
        return volume(cutter.intersect(slab)) / 0.1

    assert slice_area(20) == pytest.approx(3.141592653589793 * 1.7**2)
    assert slice_area(1) > 2 * slice_area(20)
    assert slice_area(39) > 2 * slice_area(20)
    top_faces = cutter.faces(">Z").vals()
    assert any(
        len(face.Edges()) == 6 for face in top_faces if isinstance(face, cq.Face)
    )


def test_positive_flask_and_cottle_are_single_noncolliding_solids() -> None:
    tooling = plaster_triangular_flask_tooling()
    master = tooling.master.shape()
    assert master is not None
    assert len(master.workplane().solids().vals()) == 1
    # A finite neck shoulder replaces the old point-only contact.
    shoulder_y = 140 * 0.72
    bridge = cq.Workplane("XY").box(20, 2, 40).translate((0, shoulder_y, 22.5))
    assert volume(bridge.intersect(master.workplane())) == pytest.approx(1600)
    silicone = tooling.silicone_shape().workplane()
    for section in tooling.cottle_sections():
        assert volume(section.geometry.workplane().intersect(silicone)) < 1e-6
        assert len(section.geometry.workplane().solids().vals()) == 1


@pytest.mark.parametrize("neck", [-1, 0, 50])
def test_flask_rejects_invalid_neck(neck: float) -> None:
    with pytest.raises(ValueError):
        TriangularFlaskVase(
            Millimeter(40), Millimeter(80), Millimeter(30), Millimeter(neck)
        )


def test_external_bosses_preserve_material_around_fastener_seats() -> None:
    tooling = MoldTooling(
        Box(Millimeter(30), Millimeter(26), Millimeter(20)), MoldPolarity.NEGATIVE
    )
    width, length, depth, center = tooling._cottle_dimensions()
    spec = tooling.features.fastener.spec
    boss_radius = max(spec.head_diameter, spec.nut_across_corners) / 2
    boss_radius += tooling.features.fastener_boss_wall
    y = center[1] + length / 2 + boss_radius - tooling.cottle_wall.value() / 2
    z = center[2] + depth * tooling.features.fastener_offset_fraction
    a, b = [s.geometry.workplane() for s in tooling.cottle_sections()]
    for x, shell in ((-width / 2 + 1, a), (width / 2 - 1, b)):
        # Both counterbores are empty at the axis, with a supporting ring.
        empty = cq.Workplane("XY").box(0.2, 0.2, 0.2).translate((x, y, z))
        ring = cq.Workplane("XY").box(0.2, 0.2, 0.2).translate((x, y, z + 4))
        assert volume(shell.intersect(empty)) < 1e-6
        assert volume(shell.intersect(ring)) == pytest.approx(0.008)


@pytest.mark.parametrize("purpose", list(CottlePurpose))
def test_registration_sockets_keep_inner_and_outer_wall_skins(
    purpose: CottlePurpose,
) -> None:
    tooling = MoldTooling(
        Box(Millimeter(30), Millimeter(26), Millimeter(20)),
        MoldPolarity.NEGATIVE,
        purpose=purpose,
    )
    _, length, depth, center = tooling._cottle_dimensions()
    wall = tooling.cottle_wall.value()
    b = tooling.cottle_sections()[1].geometry.workplane()
    for x, y, z in tooling._registration_pin_centers(center, length, depth):
        socket_probe = cq.Workplane("XY").box(0.2, 0.2, 0.2).translate((x + 1, y, z))
        assert volume(b.intersect(socket_probe)) < 1e-6
        for side in (-1, 1):
            skin_probe = (
                cq.Workplane("XY")
                .box(0.2, 0.2, 0.2)
                .translate((x + 1, y + side * (wall / 2 - 0.2), z))
            )
            assert volume(b.intersect(skin_probe)) == pytest.approx(0.008)


@pytest.mark.parametrize("radius", [0, -1, 1.8, 2, 3])
def test_rejects_registration_sockets_that_break_wall(radius: float) -> None:
    with pytest.raises(ValueError):
        MoldTooling(
            Box(Millimeter(30), Millimeter(26), Millimeter(20)),
            MoldPolarity.NEGATIVE,
            features=MoldFeatures(registration_pin_radius=radius),
        )


@pytest.mark.parametrize(
    "features",
    [
        MoldFeatures(registration_pin_length=100),
        MoldFeatures(registration_offset_fraction=0.49),
    ],
)
def test_rejects_registration_sockets_that_break_end_or_rim(
    features: MoldFeatures,
) -> None:
    tooling = MoldTooling(
        Box(Millimeter(30), Millimeter(26), Millimeter(20)),
        MoldPolarity.NEGATIVE,
        features=features,
    )
    with pytest.raises(ValueError, match="Registration"):
        tooling.cottle_sections()


def test_legacy_channel_depth_fraction_warns_and_does_not_disconnect_ports() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated and ignored"):
        tooling = MoldTooling(
            Box(Millimeter(30), Millimeter(26), Millimeter(20)),
            MoldPolarity.NEGATIVE,
            features=MoldFeatures(channel_depth_fraction=0.01),
        )
    silicone = tooling.silicone_shape().workplane()
    _, bounds = tooling._master_shape_and_bounds()
    top = tooling._cottle_dimensions()[2] / 2
    for x, y, radius in tooling._pour_ports(bounds):
        probe = cq.Workplane("XY").circle(radius * 0.99).extrude(top - bounds[2])
        probe = probe.translate((x, y, bounds[2]))
        assert volume(probe.intersect(silicone)) < 1e-6


@pytest.mark.parametrize(
    "features",
    [
        MoldFeatures(sprue_radius=float("nan")),
        MoldFeatures(vent_radius=0),
        MoldFeatures(vent_offset=float("inf")),
        MoldFeatures(fastener_boss_wall=-1),
        MoldFeatures(registration_clearance=float("nan")),
        MoldFeatures(fastener_offset_fraction=0.5),
        MoldFeatures(channel_depth_fraction=0),
    ],
)
def test_rejects_invalid_feature_scalars(features: MoldFeatures) -> None:
    with pytest.raises(ValueError):
        MoldTooling(
            Box(Millimeter(30), Millimeter(26), Millimeter(20)),
            MoldPolarity.NEGATIVE,
            features=features,
        )


def test_spherical_gear_ports_intersect_actual_master_and_open_silicone() -> None:
    tooling = resin_spherical_gear_tooling()
    master, bounds = tooling._master_shape_and_bounds()
    silicone = tooling.silicone_shape().workplane()
    top = bounds[5] + tooling.silicone_thickness.value()
    for x, y, radius in tooling._pour_ports(bounds):
        probe = cq.Workplane("XY").circle(radius * 0.99).extrude(top - bounds[2])
        probe = probe.translate((x, y, bounds[2]))
        assert volume(probe.intersect(master.workplane())) > 1
        assert volume(probe.intersect(silicone)) < 1e-6
