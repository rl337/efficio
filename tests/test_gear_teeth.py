import math
import os
import tempfile
import unittest

import efficio.objects.gears
from efficio.measures import Millimeter
from efficio.objects.gears import SphericalGear


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

    def test_spherical_gear_dimensions_follow_pitch(self) -> None:
        gear_16 = SphericalGear(radius=Millimeter(20), tooth_count=16)
        gear_32 = SphericalGear(radius=Millimeter(20), tooth_count=32)

        root_16, height_16, width_16, band_16 = gear_16._tooth_dimensions()
        root_32, height_32, width_32, band_32 = gear_32._tooth_dimensions()

        self.assertAlmostEqual(root_16, 18.0)
        self.assertAlmostEqual(height_16, 2.0)
        self.assertAlmostEqual(root_32, root_16)
        self.assertAlmostEqual(height_32, height_16)
        self.assertLess(width_32, width_16)
        self.assertAlmostEqual(width_16, band_16)
        self.assertAlmostEqual(width_32, band_32)

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
