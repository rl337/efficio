"""Recover issue #14's reference checks against the shared gear geometry.

The reference is a blank, not the finished six-hole, engraved reference part.
Keep a single involute implementation; do not revive the old gear module.
"""

import math
import os
import tempfile
import unittest

import cadquery as cq

from efficio.objects.gears.involute import InvoluteGearGeometry, mesh_phase
from efficio.objects.profiles import prism


class TestInvoluteReference(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = InvoluteGearGeometry(
            module=60.0 / 22.0, teeth=20, pressure_angle_degrees=20, backlash=0.0
        )

    def test_reference_radii_and_pitch_thickness(self) -> None:
        profile = self.profile
        self.assertAlmostEqual(profile.tip_radius, 30.0)
        self.assertAlmostEqual(profile.pitch_radius, 300.0 / 11.0)
        self.assertAlmostEqual(profile.root_radius, 262.5 / 11.0)
        self.assertAlmostEqual(
            profile.base_radius, profile.pitch_radius * math.cos(math.radians(20))
        )
        self.assertAlmostEqual(
            profile.half_thickness_angle(profile.pitch_radius), math.pi / 40.0
        )

    def test_reference_outline_is_mirror_symmetric(self) -> None:
        points = self.profile.outline(flank_samples=10)
        rounded = {(round(x, 8), round(y, 8)) for x, y in points}
        self.assertEqual(rounded, {(x, round(-y, 8)) for x, y in rounded})

    def test_reference_blank_is_valid_and_exports(self) -> None:
        blank = prism(self.profile.outline(flank_samples=10), 0.0, 8.0)
        solid = blank.val()
        assert isinstance(solid, cq.Shape)
        self.assertTrue(solid.isValid())
        self.assertEqual(len(solid.Solids()), 1)
        bounds = solid.BoundingBox()
        for actual, expected in zip(
            (bounds.xlen, bounds.ylen, bounds.zlen), (60.0, 60.0, 8.0)
        ):
            self.assertAlmostEqual(actual, expected, places=6)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "reference.stl")
            cq.exporters.export(blank, path)
            self.assertGreater(os.path.getsize(path), 0)

    def test_drivetrain_spur_pair_clears_through_one_tooth_pitch(self) -> None:
        pinion = prism(InvoluteGearGeometry(1.5, 12).outline(), 0.0, 5.0).val()
        gear = prism(InvoluteGearGeometry(1.5, 36).outline(), 0.0, 5.0).val()
        assert isinstance(pinion, cq.Shape)
        assert isinstance(gear, cq.Shape)
        for step in range(13):
            angle = 30.0 * step / 12.0
            phase = mesh_phase((0.0, 0.0), angle, 12, (36.0, 0.0), 36)
            with self.subTest(angle=angle):
                driver = pinion.rotate((0, 0, 0), (0, 0, 1), angle)
                driven = gear.rotate((0, 0, 0), (0, 0, 1), phase).translate(
                    (36.0, 0.0, 0.0)
                )
                self.assertLess(driver.intersect(driven).Volume(), 1e-6)
