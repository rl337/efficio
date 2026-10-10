import os
import tempfile
import unittest

from efficio.examples.mold_tooling import (
    plaster_triangular_flask_tooling,
    resin_spherical_gear_tooling,
)
from efficio.measures import Millimeter
from efficio.objects.gears import SphericalGear
from efficio.objects.mold_tooling import (
    PRUSA_MK4,
    BuildVolume,
    CottlePurpose,
    MoldPolarity,
    MoldTooling,
    PrinterProfile,
    SplitKind,
)
from efficio.objects.primitives import Box


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
        self.assertIs(tooling.purpose, CottlePurpose.BOTH)

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
        self.assertTrue(
            all(section.split_kind is SplitKind.FUNCTIONAL for section in sections)
        )
        self.assertTrue(all(section.geometry.isValid() for section in sections))
        self.assertTrue(all(section.fits(PRUSA_MK4) for section in sections))

    def test_negative_silicone_preserves_tooth_envelope(self) -> None:
        """Resin cavity block must be larger than a root-sphere fallback."""
        tooling = resin_spherical_gear_tooling()
        master = tooling.master.shape()
        assert master is not None
        master_bounds = master.bounds()
        assert master_bounds is not None
        master_dims = (
            master_bounds[3] - master_bounds[0],
            master_bounds[4] - master_bounds[1],
            master_bounds[5] - master_bounds[2],
        )

        silicone = tooling.silicone_shape()
        silicone_bounds = silicone.bounds()
        assert silicone_bounds is not None
        silicone_dims = (
            silicone_bounds[3] - silicone_bounds[0],
            silicone_bounds[4] - silicone_bounds[1],
            silicone_bounds[5] - silicone_bounds[2],
        )

        pad = tooling.silicone_thickness.value()
        for master_dim, silicone_dim in zip(master_dims, silicone_dims):
            self.assertGreater(silicone_dim, master_dim)
            self.assertAlmostEqual(silicone_dim, master_dim + 2 * pad, delta=0.5)

        # Tip envelope is ~50.8 mm; a root-only sphere would be ~45.7 mm.
        self.assertGreater(max(master_dims), 49.5)

    def test_positive_silicone_embeds_master_in_envelope(self) -> None:
        tooling = plaster_triangular_flask_tooling()
        self.assertIs(tooling.polarity, MoldPolarity.POSITIVE)
        self.assertIs(tooling.purpose, CottlePurpose.MOLD_SUPPORT)

        master = tooling.master.shape()
        assert master is not None
        master_bounds = master.bounds()
        assert master_bounds is not None
        master_dims = (
            master_bounds[3] - master_bounds[0],
            master_bounds[4] - master_bounds[1],
            master_bounds[5] - master_bounds[2],
        )

        silicone = tooling.silicone_shape()
        self.assertTrue(silicone.isValid())
        silicone_bounds = silicone.bounds()
        assert silicone_bounds is not None
        silicone_dims = (
            silicone_bounds[3] - silicone_bounds[0],
            silicone_bounds[4] - silicone_bounds[1],
            silicone_bounds[5] - silicone_bounds[2],
        )

        pad = tooling.silicone_thickness.value()
        for master_dim, silicone_dim in zip(master_dims, silicone_dims):
            self.assertAlmostEqual(silicone_dim, master_dim + 2 * pad, delta=0.5)

        tooling.validate_for_printer()
        sections = tooling.cottle_sections()
        self.assertEqual(len(sections), 2)
        self.assertTrue(all(section.geometry.isValid() for section in sections))
        self.assertTrue(all(section.fits(PRUSA_MK4) for section in sections))

    def test_cottle_has_registration_and_m3_features(self) -> None:
        tooling = resin_spherical_gear_tooling()
        width, _length, _depth, center = tooling._cottle_dimensions()
        sections = {section.name: section for section in tooling.cottle_sections()}
        self.assertEqual(set(sections), {"A", "B"})

        bounds_a = sections["A"].geometry.bounds()
        bounds_b = sections["B"].geometry.bounds()
        assert bounds_a is not None and bounds_b is not None

        # Pins on A extend across the mid-plane toward B.
        self.assertGreater(bounds_a[3], center[0])
        # B still starts at the parting plane while accepting sockets.
        self.assertAlmostEqual(bounds_b[0], center[0], delta=0.5)

        for section in sections.values():
            self.assertIs(section.split_kind, SplitKind.FUNCTIONAL)
            self.assertTrue(section.geometry.isValid())
            self.assertLess(section.dimensions()[0], width)

    def test_cottle_purpose_changes_pour_topology(self) -> None:
        gear = SphericalGear(radius=Millimeter(20), tooth_count=16)

        with_pour = MoldTooling(
            master=gear,
            polarity=MoldPolarity.NEGATIVE,
            purpose=CottlePurpose.BOTH,
        )
        support_only = MoldTooling(
            master=gear,
            polarity=MoldPolarity.NEGATIVE,
            purpose=CottlePurpose.MOLD_SUPPORT,
        )
        self.assertTrue(with_pour.silicone_shape().isValid())
        self.assertTrue(support_only.silicone_shape().isValid())
        self.assertTrue(with_pour._has_pour_features())
        self.assertFalse(support_only._has_pour_features())

        pour_only = MoldTooling(
            master=gear,
            polarity=MoldPolarity.NEGATIVE,
            purpose=CottlePurpose.POUR_CONTAINMENT,
        )
        pour_sections = pour_only.cottle_sections()
        support_sections = support_only.cottle_sections()
        pour_depth = pour_sections[0].dimensions()[2]
        support_depth = support_sections[0].dimensions()[2]
        # Open-top pour containment is shorter than a closed support cottle.
        self.assertLess(pour_depth, support_depth)

    def test_tooling_exports_silicone_and_cottle_stls_for_both_examples(
        self,
    ) -> None:
        for factory in (resin_spherical_gear_tooling, plaster_triangular_flask_tooling):
            tooling = factory()
            with tempfile.TemporaryDirectory() as directory:
                paths = tooling.export_stl_set(directory)
                self.assertEqual(len(paths), 3)
                self.assertTrue(any(path.endswith("silicone.stl") for path in paths))
                for path in paths:
                    self.assertTrue(os.path.exists(path))
                    self.assertGreater(os.path.getsize(path), 0)

    def test_oversized_tooling_requires_manufacturing_subdivision(self) -> None:
        tiny_printer = PrinterProfile(
            name="TinyTestPrinter",
            build_volume=BuildVolume(Millimeter(10), Millimeter(10), Millimeter(10)),
        )
        tooling = MoldTooling(
            master=Box(Millimeter(40), Millimeter(40), Millimeter(40)),
            polarity=MoldPolarity.NEGATIVE,
            printer=tiny_printer,
            purpose=CottlePurpose.MOLD_SUPPORT,
        )
        with self.assertRaises(ValueError) as raised:
            tooling.validate_for_printer()
        self.assertIn("manufacturing subdivision is required", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
