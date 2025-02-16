import math
import unittest

import efficio.objects.gears

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