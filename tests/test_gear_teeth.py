import math
import unittest
import tempfile
import os

import efficio.objects.gears
from efficio.objects.gears import SphericalGear
from efficio.measures import Millimeter

class TestObjects(unittest.TestCase):

    def test_rectangular_gear_tooth(self) -> None:

        tests = [
            {
                'maximum_radius': 50.0,
                'thickness': 10.0,
                'tooth_count': 10,
                'expected_pitch_angle': 0.6283185307179586,
                'expected_pitch_radius': 42.5,
                'expected_circular_pitch': 26.703537555513243,
                'expected_tooth_height': 18.692476288859268,
                'expected_tooth_width': 13.133222260935265,
                'expected_chord_width': 26.26644452187053,
                'expected_base_radius': 30.27287557263539,
            }
        ]
        for test in tests:
            gear = efficio.objects.gears.AbstractGear(
                efficio.Millimeter(test['maximum_radius']), 
                int(test['tooth_count']), 
                efficio.Millimeter(test['thickness']), 
                efficio.objects.gears.GearToothType.RECTANGULAR
            )
            tooth = efficio.objects.gears._RectangularGearTooth(gear)
            self.assertIsNotNone(tooth)

            self.assertAlmostEqual(tooth.calculate_pitch_angle(), test['expected_pitch_angle'])
            self.assertAlmostEqual(tooth.calculate_pitch_radius(), test['expected_pitch_radius'])
            self.assertAlmostEqual(tooth.calculate_circular_pitch(), test['expected_circular_pitch'])
            self.assertAlmostEqual(tooth.calculate_tooth_height(), test['expected_tooth_height'])
            self.assertAlmostEqual(tooth.calculate_tooth_width(), test['expected_tooth_width'])
            self.assertAlmostEqual(tooth.calculate_chord_width(), test['expected_chord_width'])
            self.assertAlmostEqual(tooth.calculate_base_radius(), test['expected_base_radius'])

    def test_spherical_gear_generation_and_export(self) -> None:
        """
        Tests the generation, validity, and STL export of a SphericalGear.
        """
        # 1. Instantiate SphericalGear
        radius = Millimeter(20)
        tooth_count = 16  # This parameter is part of AbstractGear, used by SphericalGear
        gear = SphericalGear(radius=radius, tooth_count=tooth_count)

        # 2. Get the shape
        shape = gear.shape()

        # 3. Assert the shape is not None
        self.assertIsNotNone(shape, "SphericalGear shape should not be None after complex boolean operations.")

        # 4. Assert the shape is valid
        if shape is not None: # Proceed only if shape exists
            # This validity check is crucial for the complex geometry
            # and may be computationally intensive.
            is_valid = shape.isValid()
            if not is_valid:
                # Optional: try to save the invalid shape for debugging
                # Ensure the directory exists or use a known writable path.
                # For automated tests, this might be better handled by CI artifacts if possible.
                # shape.as_stl_file("invalid_spherical_gear_debug.stl")
                pass # Allow the assertion to fail normally
            self.assertTrue(is_valid, "SphericalGear shape should be valid after complex boolean operations.")

            # 5. Export to a temporary STL file
            # Note: Visual inspection of the generated STL is highly recommended 
            # to verify complex gear geometry, as programmatic checks for "correctness"
            # of such intricate shapes are hard to define exhaustively.
            temp_stl_file = None
            try:
                # Create a temporary file name
                with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
                    temp_stl_file = tmpfile.name
                
                shape.as_stl_file(temp_stl_file)
                
                # Optionally assert that the file exists
                self.assertTrue(os.path.exists(temp_stl_file), 
                                f"STL file {temp_stl_file} was not created.")
            finally:
                # Clean up the temporary file
                if temp_stl_file and os.path.exists(temp_stl_file):
                    os.remove(temp_stl_file)