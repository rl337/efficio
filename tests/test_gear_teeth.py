import math
import os
import tempfile
import unittest

import efficio.objects.gears
from efficio.measures import Millimeter
from efficio.objects.gears import (\n    InvoluteGear,\n    InvoluteGearToothProfile,\n    PressureAngle,\n    SphericalGear,\n)


class TestObjects(unittest.TestCase):

    def test_rectangular_gear_tooth(self) -> None:

        tests = [
            {
                "maximum_radius": 50.0,
                "thickness": 10.0,
                "tooth_count": 10,
                "expected_pitch_angle": 0.6283185307179586,
                "expected_pitch_radius": 42.5,
                "expected_circular_pitch": 26.703537555513243,
                "expected_tooth_height": 18.692476288859268,
                "expected_tooth_width": 13.133222260935265,
                "expected_chord_width": 26.26644452187053,
                "expected_base_radius": 30.27287557263539,
            }
        ]
        for test in tests:
            gear = efficio.objects.gears.AbstractGear(
                efficio.Millimeter(test["maximum_radius"]),
                int(test["tooth_count"]),
                efficio.Millimeter(test["thickness"]),
                efficio.objects.gears.GearToothType.RECTANGULAR,
            )
            tooth = efficio.objects.gears._RectangularGearTooth(gear)
            self.assertIsNotNone(tooth)

            self.assertAlmostEqual(
                tooth.calculate_pitch_angle(), test["expected_pitch_angle"]
            )
            self.assertAlmostEqual(
                tooth.calculate_pitch_radius(), test["expected_pitch_radius"]
            )
            self.assertAlmostEqual(
                tooth.calculate_circular_pitch(), test["expected_circular_pitch"]
            )
            self.assertAlmostEqual(
                tooth.calculate_tooth_height(), test["expected_tooth_height"]
            )
            self.assertAlmostEqual(
                tooth.calculate_tooth_width(), test["expected_tooth_width"]
            )
            self.assertAlmostEqual(
                tooth.calculate_chord_width(), test["expected_chord_width"]
            )
            self.assertAlmostEqual(
                tooth.calculate_base_radius(), test["expected_base_radius"]
            )


    def test_involute_profile_uses_standard_full_depth_geometry(self) -> None:
        profile = InvoluteGearToothProfile(30.0, 20, PressureAngle.MODERN)

        self.assertAlmostEqual(profile.module, 30.0 / 11.0)
        self.assertAlmostEqual(profile.pitch_radius, profile.module * 10.0)
        self.assertAlmostEqual(profile.addendum_radius, 30.0)
        self.assertAlmostEqual(
            profile.base_radius,
            profile.pitch_radius * math.cos(math.radians(20.0)),
        )
        self.assertAlmostEqual(
            profile.root_radius,
            profile.pitch_radius - 1.25 * profile.module,
        )

        right = profile.flank_point(profile.pitch_radius, 1)
        left = profile.flank_point(profile.pitch_radius, -1)
        self.assertAlmostEqual(right[0], left[0], places=9)
        self.assertAlmostEqual(right[1], -left[1], places=9)

        pitch_half_angle = math.atan2(right[1], right[0])
        self.assertAlmostEqual(
            pitch_half_angle,
            math.pi / (2.0 * profile.tooth_count),
            places=9,
        )

    def test_involute_spur_gear_generation_and_export(self) -> None:
        gear = InvoluteGear(
            radius=Millimeter(30),
            tooth_count=20,
            thickness=Millimeter(8),
            pressure_angle=PressureAngle.MODERN,
        )
        shape = gear.shape()
        self.assertIsNotNone(shape)
        if shape is None:
            self.fail("InvoluteGear unexpectedly returned no shape")

        self.assertTrue(shape.isValid())
        bounds = shape.bounds()
        self.assertIsNotNone(bounds)
        if bounds is None:
            self.fail("InvoluteGear unexpectedly has no bounds")

        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        self.assertAlmostEqual(max_x - min_x, 60.0, delta=0.1)
        self.assertAlmostEqual(max_y - min_y, 60.0, delta=0.1)
        self.assertAlmostEqual(max_z - min_z, 8.0, delta=0.01)

        temp_stl_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
                temp_stl_file = tmpfile.name
            shape.as_stl_file(temp_stl_file)
            self.assertGreater(os.path.getsize(temp_stl_file), 0)
        finally:
            if temp_stl_file and os.path.exists(temp_stl_file):
                os.remove(temp_stl_file)

    def test_spherical_gear_surface_is_periodic_and_bounded(self) -> None:
        gear = SphericalGear(radius=Millimeter(20), tooth_count=16)
        root = gear._root_radius()
        self.assertAlmostEqual(root, 18.0)

        # Every sampled direction must remain inside the requested 20 mm tip
        # envelope and outside the 18 mm root envelope.
        for theta_index in range(1, 12):
            theta = math.pi * theta_index / 12
            for phi_index in range(32):
                phi = 2 * math.pi * phi_index / 32
                direction = (
                    math.sin(theta) * math.cos(phi),
                    math.sin(theta) * math.sin(phi),
                    math.cos(theta),
                )
                radius = gear._surface_radius(*direction)
                self.assertGreaterEqual(radius, root - 1e-9)
                self.assertLessEqual(radius, 20.0 + 1e-9)

        # A one-tooth rotation around a principal axis repeats the field.
        phi = 0.137
        pitch = 2 * math.pi / gear.get_tooth_count()
        first = gear._surface_radius(math.cos(phi), math.sin(phi), 0.0)
        repeated = gear._surface_radius(
            math.cos(phi + pitch), math.sin(phi + pitch), 0.0
        )
        self.assertAlmostEqual(first, repeated, places=9)

    def test_spherical_gear_orthogonal_tooth_families_are_symmetric(self) -> None:
        gear = SphericalGear(radius=Millimeter(20), tooth_count=16)
        sample = (0.81, 0.48, 0.33)
        length = math.sqrt(sum(value * value for value in sample))
        x, y, z = (value / length for value in sample)

        base = gear._surface_radius(x, y, z)
        self.assertAlmostEqual(base, gear._surface_radius(y, x, z), places=9)
        self.assertAlmostEqual(base, gear._surface_radius(x, z, y), places=9)

    def test_spherical_gear_rejects_too_few_teeth(self) -> None:
        with self.assertRaises(ValueError):
            SphericalGear(radius=Millimeter(20), tooth_count=3)

    def test_spherical_gear_generation_and_export(self) -> None:
        """Spherical gear should be valid, toothed, symmetric, and exportable."""
        radius = Millimeter(20)
        gear = SphericalGear(radius=radius, tooth_count=16)
        shape = gear.shape()

        self.assertIsNotNone(shape)
        if shape is None:
            self.fail("SphericalGear unexpectedly returned no shape")

        self.assertTrue(shape.isValid(), "Spherical gear should be valid CAD geometry")
        bounds = shape.bounds()
        self.assertIsNotNone(bounds)
        if bounds is None:
            self.fail("SphericalGear unexpectedly has no bounds")

        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        dimensions = (max_x - min_x, max_y - min_y, max_z - min_z)

        # Three orthogonal copies of the same great-circle band should produce
        # essentially identical extents on all axes.
        self.assertAlmostEqual(dimensions[0], dimensions[1], delta=0.05)
        self.assertAlmostEqual(dimensions[1], dimensions[2], delta=0.05)

        # The requested radius is the tooth-tip radius, not the root sphere.
        expected_diameter = 2 * radius.value()
        for dimension in dimensions:
            self.assertAlmostEqual(dimension, expected_diameter, delta=0.1)

        # A plain fallback sphere at the root radius would only be 36 mm across.
        self.assertGreater(max(dimensions), 39.5)

        temp_stl_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
                temp_stl_file = tmpfile.name

            shape.as_stl_file(temp_stl_file)
            self.assertTrue(os.path.exists(temp_stl_file))
            self.assertGreater(os.path.getsize(temp_stl_file), 0)
        finally:
            if temp_stl_file and os.path.exists(temp_stl_file):
                os.remove(temp_stl_file)
