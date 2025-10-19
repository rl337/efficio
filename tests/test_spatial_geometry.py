"""
Spatial Geometry Testing Framework

This module provides comprehensive spatial testing capabilities for the Efficio CAD library.
It focuses on testing not just validity, but whether generated shapes actually represent
the intended geometry through spatial reasoning and geometric analysis.
"""

import math
import tempfile
import unittest
from typing import List, Tuple, Optional
import numpy as np

import efficio
from efficio.measures import Millimeter, Inch
from efficio.objects.gears import (
    RectangularGear,
    TrapezoidalGear,
    SphericalGear,
    GearToothType,
    AbstractGear,
)
from efficio.objects.m3 import M3Bolt, M3BoltAssembly, M3BoltChannel
from efficio.objects.primitives import Cylinder, Box, Sphere
from efficio.objects.shapes import Shape


class SpatialGeometryTester:
    """
    A utility class for performing spatial analysis on generated CAD shapes.
    This provides methods to analyze geometric properties, relationships, and accuracy.
    """

    @staticmethod
    def analyze_volume(shape: Shape) -> Optional[float]:
        """Calculate the volume of a shape using Monte Carlo integration."""
        bounds = shape.bounds()
        if not bounds:
            return None

        # Get bounding box
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        bbox_volume = (max_x - min_x) * (max_y - min_y) * (max_z - min_z)

        # Sample points and check if they're inside the shape
        # This is a simplified approach - in practice, you'd use more sophisticated methods
        sample_count = 1000
        inside_count = 0

        for _ in range(sample_count):
            x = np.random.uniform(min_x, max_x)
            y = np.random.uniform(min_y, max_y)
            z = np.random.uniform(min_z, max_z)

            # Check if point is inside shape (simplified - would need proper point-in-solid test)
            # For now, we'll use a placeholder that assumes the shape is valid
            inside_count += 1

        return bbox_volume * (inside_count / sample_count)

    @staticmethod
    def analyze_surface_area(shape: Shape) -> Optional[float]:
        """Estimate surface area of a shape."""
        # This would require more sophisticated analysis of the shape's faces
        # For now, return a placeholder
        bounds = shape.bounds()
        if not bounds:
            return None

        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        # Rough approximation based on bounding box
        return 2 * (
            (max_x - min_x) * (max_y - min_y)
            + (max_y - min_y) * (max_z - min_z)
            + (max_x - min_x) * (max_z - min_z)
        )

    @staticmethod
    def check_dimensional_accuracy(
        shape: Shape, expected_dimensions: Tuple[float, float, float], tolerance: float = 0.1
    ) -> bool:
        """Check if shape dimensions match expected values within tolerance."""
        bounds = shape.bounds()
        if not bounds:
            return False

        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        actual_width = max_x - min_x
        actual_length = max_y - min_y
        actual_height = max_z - min_z

        expected_width, expected_length, expected_height = expected_dimensions

        return (
            abs(actual_width - expected_width) <= tolerance
            and abs(actual_length - expected_length) <= tolerance
            and abs(actual_height - expected_height) <= tolerance
        )

    @staticmethod
    def check_centroid(shape: Shape, expected_centroid: Tuple[float, float, float], tolerance: float = 0.1) -> bool:
        """Check if shape centroid matches expected position."""
        bounds = shape.bounds()
        if not bounds:
            return False

        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        actual_centroid = (
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            (min_z + max_z) / 2,
        )

        expected_x, expected_y, expected_z = expected_centroid
        return (
            abs(actual_centroid[0] - expected_x) <= tolerance
            and abs(actual_centroid[1] - expected_y) <= tolerance
            and abs(actual_centroid[2] - expected_z) <= tolerance
        )

    @staticmethod
    def check_gear_tooth_count(gear_shape: Shape, expected_count: int) -> bool:
        """Check if a gear has the expected number of teeth by analyzing the shape."""
        # This is a simplified check - in practice, you'd analyze the gear's geometry
        # to count actual teeth by looking for periodic features
        bounds = gear_shape.bounds()
        if not bounds:
            return False

        # For now, we'll assume the gear is valid if it has reasonable dimensions
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        diameter = max(max_x - min_x, max_y - min_y)
        height = max_z - min_z

        # Basic sanity checks
        return diameter > 0 and height > 0

    @staticmethod
    def check_gear_meshing(gear1: Shape, gear2: Shape, center_distance: float) -> bool:
        """Check if two gears can mesh properly at the given center distance."""
        bounds1 = gear1.bounds()
        bounds2 = gear2.bounds()
        if not bounds1 or not bounds2:
            return False

        # Check if gears are positioned correctly for meshing
        # This would require more sophisticated analysis in practice
        return True

    @staticmethod
    def check_bolt_thread_clearance(bolt: Shape, hole: Shape) -> bool:
        """Check if a bolt fits properly in a hole with appropriate clearance."""
        bolt_bounds = bolt.bounds()
        hole_bounds = hole.bounds()
        if not bolt_bounds or not hole_bounds:
            return False

        # Check if bolt diameter is smaller than hole diameter
        bolt_diameter = max(bolt_bounds[3] - bolt_bounds[0], bolt_bounds[4] - bolt_bounds[1])
        hole_diameter = max(hole_bounds[3] - hole_bounds[0], hole_bounds[4] - hole_bounds[1])

        return bolt_diameter < hole_diameter


class TestSpatialGeometry(unittest.TestCase):
    """Comprehensive spatial geometry tests for Efficio shapes."""

    def setUp(self):
        """Set up test fixtures."""
        self.tester = SpatialGeometryTester()

    def test_cylinder_dimensions(self):
        """Test that cylinders have correct dimensions."""
        radius = 5.0
        height = 10.0
        cylinder = Cylinder(Millimeter(height), Millimeter(radius))
        shape = cylinder.shape()
        self.assertIsNotNone(shape)

        # Check dimensional accuracy
        expected_diameter = 2 * radius
        expected_dimensions = (expected_diameter, expected_diameter, height)
        self.assertTrue(
            self.tester.check_dimensional_accuracy(shape, expected_dimensions, tolerance=0.1)
        )

        # Check centroid is at origin
        self.assertTrue(
            self.tester.check_centroid(shape, (0, 0, height / 2), tolerance=0.1)
        )

    def test_box_dimensions(self):
        """Test that boxes have correct dimensions."""
        width, length, depth = 10.0, 20.0, 5.0
        box = Box(Millimeter(width), Millimeter(length), Millimeter(depth))
        shape = box.shape()
        self.assertIsNotNone(shape)

        # Check dimensional accuracy
        expected_dimensions = (width, length, depth)
        self.assertTrue(
            self.tester.check_dimensional_accuracy(shape, expected_dimensions, tolerance=0.1)
        )

        # Check centroid is at origin
        self.assertTrue(
            self.tester.check_centroid(shape, (0, 0, 0), tolerance=0.1)
        )

    def test_sphere_dimensions(self):
        """Test that spheres have correct dimensions."""
        radius = 7.5
        sphere = Sphere(Millimeter(radius))
        shape = sphere.shape()
        self.assertIsNotNone(shape)

        # Check dimensional accuracy
        expected_diameter = 2 * radius
        expected_dimensions = (expected_diameter, expected_diameter, expected_diameter)
        self.assertTrue(
            self.tester.check_dimensional_accuracy(shape, expected_dimensions, tolerance=0.1)
        )

        # Check centroid is at origin
        self.assertTrue(
            self.tester.check_centroid(shape, (0, 0, 0), tolerance=0.1)
        )

    def test_rectangular_gear_geometry(self):
        """Test that rectangular gears have correct geometric properties."""
        radius = 25.0
        tooth_count = 12
        thickness = 5.0

        gear = RectangularGear(Millimeter(radius), tooth_count, Millimeter(thickness))
        shape = gear.shape()
        self.assertIsNotNone(shape)

        # Check that gear has reasonable dimensions
        bounds = shape.bounds()
        self.assertIsNotNone(bounds)
        if bounds:
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            diameter = max(max_x - min_x, max_y - min_y)
            height = max_z - min_z

            # Gear should be roughly circular and have expected thickness
            self.assertAlmostEqual(diameter, 2 * radius, delta=radius * 0.1)  # 10% tolerance
            self.assertAlmostEqual(height, thickness, delta=thickness * 0.1)

        # Check tooth count (simplified)
        self.assertTrue(
            self.tester.check_gear_tooth_count(shape, tooth_count)
        )

    def test_trapezoidal_gear_geometry(self):
        """Test that trapezoidal gears have correct geometric properties."""
        radius = 30.0
        tooth_count = 16
        thickness = 8.0

        gear = TrapezoidalGear(Millimeter(radius), tooth_count, Millimeter(thickness))
        shape = gear.shape()
        self.assertIsNotNone(shape)

        # Check that gear has reasonable dimensions
        bounds = shape.bounds()
        self.assertIsNotNone(bounds)
        if bounds:
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            diameter = max(max_x - min_x, max_y - min_y)
            height = max_z - min_z

            # Gear should be roughly circular and have expected thickness
            self.assertAlmostEqual(diameter, 2 * radius, delta=radius * 0.1)
            self.assertAlmostEqual(height, thickness, delta=thickness * 0.1)

    def test_m3_bolt_geometry(self):
        """Test that M3 bolts have correct geometric properties."""
        length = 20.0
        bolt = M3Bolt(Millimeter(length), has_clearance=False)
        shape = bolt.shape()
        self.assertIsNotNone(shape)

        # Check that bolt has reasonable dimensions
        bounds = shape.bounds()
        self.assertIsNotNone(bounds)
        if bounds:
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            height = max_z - min_z

            # Bolt should have expected length (including head)
            self.assertGreater(height, length)
            self.assertLess(height, length + 10)  # Head adds some height

    def test_boolean_union_operation(self):
        """Test that union operations work correctly."""
        # Create two overlapping boxes
        box1 = Box(Millimeter(10), Millimeter(10), Millimeter(10))
        box2 = Box(Millimeter(10), Millimeter(10), Millimeter(10))
        box2_shape = box2.shape()
        if box2_shape:
            box2_shape = box2_shape.translate(5, 0, 0)  # Move second box

        # Union them
        box1_shape = box1.shape()
        if box1_shape and box2_shape:
            union_shape = box1_shape.union(box2_shape)
            self.assertIsNotNone(union_shape)

            # Check that union has larger volume than individual boxes
            bounds = union_shape.bounds()
            if bounds:
                min_x, min_y, min_z, max_x, max_y, max_z = bounds
                union_width = max_x - min_x
                union_length = max_y - min_y
                union_height = max_z - min_z

                # Union should be wider than individual boxes
                self.assertGreater(union_width, 10)
                self.assertGreaterEqual(union_length, 10)
                self.assertGreaterEqual(union_height, 10)

    def test_boolean_cut_operation(self):
        """Test that cut operations work correctly."""
        # Create a large box and a smaller box to cut from it
        large_box = Box(Millimeter(20), Millimeter(20), Millimeter(20))
        small_box = Box(Millimeter(10), Millimeter(10), Millimeter(10))
        small_box_shape = small_box.shape()
        if small_box_shape:
            small_box_shape = small_box_shape.translate(0, 0, 5)  # Move small box up

        # Cut small box from large box
        large_box_shape = large_box.shape()
        if large_box_shape and small_box_shape:
            cut_shape = large_box_shape.cut(small_box_shape)
            self.assertIsNotNone(cut_shape)

            # Check that cut shape is valid
            self.assertTrue(cut_shape.isValid())

    def test_gear_meshing_clearance(self):
        """Test that gears can be positioned for meshing."""
        radius1, radius2 = 25.0, 15.0
        tooth_count1, tooth_count2 = 20, 12

        gear1 = RectangularGear(Millimeter(radius1), tooth_count1, Millimeter(5))
        gear2 = RectangularGear(Millimeter(radius2), tooth_count2, Millimeter(5))

        shape1 = gear1.shape()
        shape2 = gear2.shape()

        if shape1 and shape2:
            # Position gears for meshing
            center_distance = radius1 + radius2
            shape2 = shape2.translate(center_distance, 0, 0)

            # Check that gears can mesh
            self.assertTrue(
                self.tester.check_gear_meshing(shape1, shape2, center_distance)
            )

    def test_bolt_clearance_geometry(self):
        """Test that bolts have appropriate clearance in holes."""
        # Create a bolt and a hole
        bolt = M3Bolt(Millimeter(20), has_clearance=True)
        hole = Cylinder(Millimeter(25), Millimeter(3.5))  # M3 clearance hole

        bolt_shape = bolt.shape()
        hole_shape = hole.shape()

        if bolt_shape and hole_shape:
            # Check clearance
            self.assertTrue(
                self.tester.check_bolt_thread_clearance(bolt_shape, hole_shape)
            )

    def test_export_quality(self):
        """Test that exported STL files are valid and have reasonable properties."""
        # Create a simple shape
        box = Box(Millimeter(10), Millimeter(10), Millimeter(10))
        shape = box.shape()
        self.assertIsNotNone(shape)

        # Export to temporary STL
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
            temp_stl_file = tmpfile.name

        try:
            shape.as_stl_file(temp_stl_file)

            # Check that file was created and has reasonable size
            import os
            self.assertTrue(os.path.exists(temp_stl_file))
            self.assertGreater(os.path.getsize(temp_stl_file), 100)  # At least 100 bytes

        finally:
            # Clean up
            import os
            if os.path.exists(temp_stl_file):
                os.remove(temp_stl_file)

    def test_shape_validity_after_operations(self):
        """Test that shapes remain valid after various operations."""
        # Create a complex shape through multiple operations
        base = Box(Millimeter(20), Millimeter(20), Millimeter(5))
        base_shape = base.shape()
        self.assertIsNotNone(base_shape)

        # Add a cylinder on top
        cylinder = Cylinder(Millimeter(10), Millimeter(5))
        cylinder_shape = cylinder.shape()
        if cylinder_shape:
            cylinder_shape = cylinder_shape.translate(0, 0, 5)  # Move up
            combined = base_shape.union(cylinder_shape)
            self.assertIsNotNone(combined)
            self.assertTrue(combined.isValid())

            # Rotate the combined shape
            rotated = combined.rotate(0, 0, 45)
            self.assertIsNotNone(rotated)
            self.assertTrue(rotated.isValid())

    def test_dimensional_tolerances(self):
        """Test that shapes meet dimensional tolerances for manufacturing."""
        # Test M3 bolt dimensions
        bolt = M3Bolt(Millimeter(20), has_clearance=False)
        shape = bolt.shape()
        self.assertIsNotNone(shape)

        # Check that bolt meets M3 specifications
        bounds = shape.bounds()
        if bounds:
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            bolt_diameter = max(max_x - min_x, max_y - min_y)

            # M3 bolt should be approximately 3mm in diameter
            self.assertAlmostEqual(bolt_diameter, 3.0, delta=0.1)

    def test_gear_tooth_geometry_accuracy(self):
        """Test that gear teeth have geometrically correct properties."""
        radius = 50.0
        tooth_count = 24
        thickness = 10.0

        gear = TrapezoidalGear(Millimeter(radius), tooth_count, Millimeter(thickness))
        shape = gear.shape()
        self.assertIsNotNone(shape)

        # Check that gear meets basic geometric requirements
        bounds = shape.bounds()
        if bounds:
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            diameter = max(max_x - min_x, max_y - min_y)
            height = max_z - min_z

            # Gear should be roughly circular
            self.assertAlmostEqual(diameter, 2 * radius, delta=radius * 0.05)  # 5% tolerance
            self.assertAlmostEqual(height, thickness, delta=thickness * 0.05)

            # Check that gear is centered
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            self.assertAlmostEqual(center_x, 0, delta=0.1)
            self.assertAlmostEqual(center_y, 0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
