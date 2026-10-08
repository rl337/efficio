import unittest

from efficio.measures import Millimeter
from efficio.objects.gear_markings import (
    GearArcMarking,
    GearFaceMarker,
    standard_involute_markings,
)
from efficio.objects.gears import InvoluteGear, InvoluteGearToothProfile, PressureAngle


class TestGearFaceMarkings(unittest.TestCase):
    def test_character_order_is_clockwise_and_independent_of_orientation(self) -> None:
        marker = GearFaceMarker(thickness=8.0)
        marking = GearArcMarking("efficio", 22.0, 90.0, 62.0, 3.4)
        angles = marker.character_angles(marking)

        self.assertEqual(len(angles), len("efficio"))
        self.assertGreater(angles[0], angles[-1])
        self.assertAlmostEqual((angles[0] + angles[-1]) / 2.0, 90.0)

    def test_standard_marking_contains_mating_parameters(self) -> None:
        profile = InvoluteGearToothProfile(30.0, 20, PressureAngle.MODERN)
        markings = standard_involute_markings(
            tooth_count=20,
            module=profile.module,
            pressure_angle_degrees=20.0,
            marking_radius=22.0,
        )

        self.assertEqual(markings[0].text, "efficio")
        self.assertEqual(markings[1].text, "20T M2.727 PA20")

    def test_marking_preserves_valid_spur_gear_solid(self) -> None:
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
            self.fail("Marked gear unexpectedly has no bounds")
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        self.assertAlmostEqual(max_x - min_x, 60.0, delta=0.1)
        self.assertAlmostEqual(max_y - min_y, 60.0, delta=0.1)
        self.assertAlmostEqual(max_z - min_z, 8.0, delta=0.01)

    def test_automatic_engraving_removes_material(self) -> None:
        options = dict(radius=Millimeter(30), tooth_count=20, thickness=Millimeter(8))
        marked = InvoluteGear(**options, engrave_identity=True).shape()
        plain = InvoluteGear(**options, engrave_identity=False).shape()
        self.assertIsNotNone(marked)
        self.assertIsNotNone(plain)
        self.assertTrue(marked.isValid())
        self.assertTrue(plain.isValid())
        self.assertLess(marked.workplane().val().Volume(), plain.workplane().val().Volume())


if __name__ == "__main__":
    unittest.main()
