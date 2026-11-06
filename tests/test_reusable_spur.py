"""Reconciled issue #14 capabilities use the shared PR #27 gear engine."""

import math
import os
import tempfile
import unittest
from dataclasses import replace

import cadquery as cq

from efficio.__main__ import main
from efficio.measures import Millimeter
from efficio.objects.gears import InvoluteGearGeometry, MetricModule, SpurGear
from efficio.objects.gears.markings import GearFaceMarker


def solid(gear: SpurGear) -> cq.Shape:
    shape = gear.shape()
    assert shape is not None
    value = shape.workplane().val()
    assert isinstance(value, cq.Shape)
    assert value.isValid()
    assert len(value.Solids()) == 1
    return value


class TestReusableProfile(unittest.TestCase):
    def test_single_tooth_and_whole_outline_share_points(self) -> None:
        profile = InvoluteGearGeometry.from_tip_radius(30, 20)
        tooth = profile.tooth_outline()
        self.assertEqual(profile.outline()[: len(tooth)], tooth)
        for radius in (profile.base_radius, profile.pitch_radius, profile.tip_radius):
            x, y = profile.flank_point(radius, 1)
            reflected = profile.flank_point(radius, -1)
            self.assertAlmostEqual(x, reflected[0])
            self.assertAlmostEqual(y, -reflected[1])
        self.assertAlmostEqual(profile.tip_radius, 30)

    def test_invalid_geometry_and_samples_rejected(self) -> None:
        for options in (
            {"module": float("nan")},
            {"pressure_angle_degrees": 90},
            {"pressure_angle_degrees": float("nan")},
            {"backlash": -1},
            {"addendum_coefficient": 0},
            {"dedendum_coefficient": 10},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                replace(InvoluteGearGeometry(1.0, 20), **options)
        profile = InvoluteGearGeometry(1.0, 20)
        for samples in (0, 1, -2):
            with self.assertRaises(ValueError):
                profile.tooth_outline(samples)
        with self.assertRaises(ValueError):
            profile.outline(root_samples=-1)
        with self.assertRaises(ValueError):
            profile.flank_point(profile.base_radius - 0.1, 1)
        with self.assertRaises(ValueError):
            profile.flank_point(profile.tip_radius, 0)
        with self.assertRaises(ValueError):
            InvoluteGearGeometry.from_tip_radius(0, 20)


class TestReusableSpur(unittest.TestCase):
    def test_custom_module_and_tip_radius_construction_agree(self) -> None:
        reference = SpurGear.from_tip_radius(Millimeter(30), 20, Millimeter(8))
        custom = SpurGear(
            reference.geometry().module,
            20,
            Millimeter(8),
            Millimeter(0),
            False,
            reference.pressure_angle,
            backlash=Millimeter(0),
        )
        self.assertEqual(reference.geometry(), custom.geometry())
        self.assertAlmostEqual(
            solid(reference).Volume(), solid(custom).Volume(), places=6
        )
        bounds = solid(reference).BoundingBox()
        self.assertAlmostEqual(bounds.xlen, 60)
        self.assertAlmostEqual(bounds.ylen, 60)
        self.assertAlmostEqual(bounds.zlen, 8)

    def test_catalogue_and_numeric_module_agree(self) -> None:
        args = (20, Millimeter(8), Millimeter(5), False)
        standard = SpurGear(MetricModule.MODULE_1_5, *args)
        numeric = SpurGear(1.5, *args)
        self.assertEqual(standard.geometry(), numeric.geometry())
        self.assertAlmostEqual(solid(standard).Volume(), solid(numeric).Volume())
        self.assertFalse(standard.engrave_identity)
        self.assertEqual(standard.lightening_hole_layout(), [])

    def test_lightening_holes_have_real_webs_and_remove_expected_volume(self) -> None:
        plain = SpurGear.from_tip_radius(Millimeter(30), 20, Millimeter(8))
        light = SpurGear.from_tip_radius(
            Millimeter(30), 20, Millimeter(8), lightening_holes=6
        )
        holes = light.lightening_hole_layout()
        self.assertEqual(len(holes), 6)
        web = light.minimum_web.value()
        for i, (x, y, radius) in enumerate(holes):
            self.assertGreaterEqual(
                light.geometry().root_radius - math.hypot(x, y) - radius, web - 1e-8
            )
            for xx, yy, other in holes[i + 1 :]:
                self.assertGreaterEqual(
                    math.hypot(x - xx, y - yy) - radius - other, web - 1e-8
                )
        removed = solid(plain).Volume() - solid(light).Volume()
        self.assertAlmostEqual(
            removed, sum(math.pi * r * r * 8 for _, _, r in holes), places=5
        )

    def test_automatic_markings_remove_material_and_avoid_holes(self) -> None:
        marked = SpurGear.from_tip_radius(
            Millimeter(30), 20, Millimeter(8), lightening_holes=6, engrave_identity=True
        )
        markings = marked.identity_markings()
        self.assertEqual(len(markings), 2)
        self.assertEqual(markings[1].text, "20T M2.727 PA20")
        marker = GearFaceMarker(8, marked.marking_style)
        holes = marked.lightening_hole_layout()
        self.assertEqual(len(holes), 6)
        hole_edge = max(math.hypot(x, y) + r for x, y, r in holes)
        for marking in markings:
            inner, outer = marker.radial_bounds(marking)
            self.assertGreaterEqual(
                inner, hole_edge + marked.marking_clearance.value() - 1e-8
            )
            self.assertLess(outer, marked.geometry().root_radius)
        plain = SpurGear.from_tip_radius(
            Millimeter(30),
            20,
            Millimeter(8),
            lightening_holes=6,
            engrave_identity=False,
        )
        self.assertEqual(plain.lightening_hole_layout(), holes)
        before = solid(plain)
        after = solid(marked)
        self.assertGreater(before.Volume() - after.Volume(), 1)
        self.assertAlmostEqual(after.BoundingBox().zlen, 8)

    def test_small_and_thin_gears_skip_markings(self) -> None:
        for radius, thickness in ((6.0, 2.0), (30.0, 0.3)):
            gear = SpurGear.from_tip_radius(
                Millimeter(radius),
                20,
                Millimeter(thickness),
                lightening_holes=6,
                engrave_identity=True,
            )
            self.assertEqual(gear.identity_markings(), [])
            solid(gear)

    def test_cli_accepts_catalogue_and_numeric_modules(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for module in ("MODULE_1_5", "2.727272727272727"):
                path = os.path.join(folder, module + ".stl")
                main(
                    "SpurGear",
                    [
                        ("module", module),
                        ("teeth", "20"),
                        ("thickness", "8mm"),
                        ("bore", "0mm"),
                        ("d_flat", "false"),
                    ],
                    None,
                    path,
                )
                self.assertGreater(os.path.getsize(path), 0)


class TestSampledRootClearance(unittest.TestCase):
    def test_holes_preserve_web_against_actual_polygon_segments(self) -> None:
        # These tooth counts put a hole near an inscribed root chord; checking
        # only root_radius previously left webs slightly below the requested 3 mm.
        for teeth in (13, 14):
            with self.subTest(teeth=teeth):
                gear = SpurGear.from_tip_radius(
                    Millimeter(30), teeth, Millimeter(8), lightening_holes=6
                )
                profile = gear.geometry()
                self.assertLess(profile.material_disc_radius(), profile.root_radius)
                points = profile.outline()
                holes = gear.lightening_hole_layout()
                self.assertEqual(len(holes), 6)
                for cx, cy, radius in holes:
                    for (x, y), (xx, yy) in zip(points, points[1:] + points[:1]):
                        dx, dy = xx - x, yy - y
                        fraction = max(
                            0.0,
                            min(
                                1.0,
                                -((x - cx) * dx + (y - cy) * dy) / (dx * dx + dy * dy),
                            ),
                        )
                        web = (
                            math.hypot(x + fraction * dx - cx, y + fraction * dy - cy)
                            - radius
                        )
                        self.assertGreaterEqual(web, gear.minimum_web.value() - 1e-8)
