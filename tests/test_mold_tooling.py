import os
import tempfile
import unittest

from efficio.examples.mold_tooling import (
    plaster_triangular_flask_tooling,
    resin_spherical_gear_tooling,
)
from efficio.measures import Millimeter
from efficio.objects.mold_tooling import PRUSA_MK4, BuildVolume, MoldPolarity


class TestMoldTooling(unittest.TestCase):
    def test_prusa_mk4_profile(self) -> None:
        volume = PRUSA_MK4.build_volume
        self.assertEqual(volume.x.value(), 250)
        self.assertEqual(volume.y.value(), 210)
        self.assertEqual(volume.z.value(), 220)

    def test_build_volume_accepts_rotated_fit(self) -> None:
        volume = BuildVolume(Millimeter(250), Millimeter(210), Millimeter(220))
        self.assertTrue(volume.fits((200, 240, 100)))
        self.assertFalse(volume.fits((260, 240, 100)))

    def test_resin_gear_is_two_inch_negative_mold(self) -> None:
        tooling = resin_spherical_gear_tooling()
        self.assertIs(tooling.polarity, MoldPolarity.NEGATIVE)

        master = tooling.master.shape()
        self.assertIsNotNone(master)
        if master is None:
            self.fail("Gear master produced no shape")
        bounds = master.bounds()
        self.assertIsNotNone(bounds)
        if bounds is None:
            self.fail("Gear master produced no bounds")
        dimensions = (
            bounds[3] - bounds[0],
            bounds[4] - bounds[1],
            bounds[5] - bounds[2],
        )
        for dimension in dimensions:
            self.assertAlmostEqual(dimension, 50.8, delta=0.2)

        silicone = tooling.silicone_shape()
        self.assertTrue(silicone.isValid())
        tooling.validate_for_printer()
        sections = tooling.cottle_sections()
        self.assertEqual([section.name for section in sections], ["A", "B"])
        self.assertTrue(all(section.geometry.isValid() for section in sections))
        self.assertTrue(all(section.fits(PRUSA_MK4) for section in sections))

    def test_plaster_vase_uses_positive_silicone_intermediate(self) -> None:
        tooling = plaster_triangular_flask_tooling()
        self.assertIs(tooling.polarity, MoldPolarity.POSITIVE)
        silicone = tooling.silicone_shape()
        self.assertTrue(silicone.isValid())
        tooling.validate_for_printer()
        sections = tooling.cottle_sections()
        self.assertEqual(len(sections), 2)
        self.assertTrue(all(section.geometry.isValid() for section in sections))
        self.assertTrue(all(section.fits(PRUSA_MK4) for section in sections))

    def test_tooling_exports_silicone_and_cottle_stls(self) -> None:
        tooling = resin_spherical_gear_tooling()
        with tempfile.TemporaryDirectory() as directory:
            silicone_path = os.path.join(directory, "silicone.stl")
            tooling.silicone_shape().as_stl_file(silicone_path)
            self.assertGreater(os.path.getsize(silicone_path), 0)

            for section in tooling.cottle_sections():
                path = os.path.join(directory, f"cottle-{section.name}.stl")
                section.geometry.as_stl_file(path)
                self.assertGreater(os.path.getsize(path), 0)


if __name__ == "__main__":
    unittest.main()
