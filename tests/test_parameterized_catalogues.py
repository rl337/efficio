"""Pure-Python tests for the catalogues and parameters added by the
parameterized-objects skill: no CadQuery needed."""

import unittest

from efficio.machines import (
    MAKERA_Z1,
    PRUSA_MK4,
    BuildVolume,
    MachineKind,
    StandardMachine,
)
from efficio.measures import Millimeter
from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.powertrain.differential.geometry import SpurDifferentialGeometry
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.layout import DrivetrainLayout, PlateSide


class TestMetricThreadCatalogue(unittest.TestCase):
    def test_m3_matches_iso_values(self) -> None:
        m3 = MetricThread.M3.spec
        self.assertEqual(m3.designation, "M3")
        self.assertAlmostEqual(m3.major_diameter, 3.0)
        self.assertAlmostEqual(m3.pitch, 0.5)
        self.assertAlmostEqual(m3.head_diameter, 5.5)
        self.assertAlmostEqual(m3.radius, 1.5)
        self.assertAlmostEqual(m3.clearance_radius, 1.7)

    def test_sizes_grow_monotonically(self) -> None:
        specs = [thread.spec for thread in MetricThread]
        for small, large in zip(specs, specs[1:]):
            self.assertLess(small.major_diameter, large.major_diameter)
            self.assertLess(small.head_diameter, large.head_diameter)
            self.assertLess(small.nut_across_flats, large.nut_across_flats)

    def test_every_spec_is_self_consistent(self) -> None:
        for thread in MetricThread:
            spec = thread.spec
            with self.subTest(thread=thread.name):
                self.assertTrue(spec.designation.startswith("M"))
                self.assertLess(spec.tap_drill, spec.major_diameter)
                self.assertGreater(spec.clearance_hole, spec.major_diameter)
                self.assertGreater(spec.head_diameter, spec.clearance_hole)
                self.assertGreater(spec.nut_across_corners, spec.nut_across_flats)
                self.assertGreater(spec.pocket_depth(), spec.nut_height)
                self.assertGreater(
                    spec.pocket_across_corners(), spec.nut_across_corners
                )


class TestMachineCatalogue(unittest.TestCase):
    def test_constants_are_catalogue_entries(self) -> None:
        self.assertIs(PRUSA_MK4, StandardMachine.PRUSA_MK4.spec)
        self.assertIs(MAKERA_Z1, StandardMachine.MAKERA_Z1.spec)
        self.assertEqual(PRUSA_MK4.kind, MachineKind.FDM_PRINTER)
        self.assertEqual(MAKERA_Z1.kind, MachineKind.CNC_MILL)
        self.assertEqual(
            StandardMachine.MAKERA_Z1_4TH_AXIS.spec.kind, MachineKind.CNC_ROTARY
        )

    def test_fits_any_orientation(self) -> None:
        volume = BuildVolume(Millimeter(100), Millimeter(50), Millimeter(20))
        self.assertTrue(volume.fits((20.0, 100.0, 50.0)))
        self.assertFalse(volume.fits((101.0, 10.0, 10.0)))
        self.assertTrue(PRUSA_MK4.build_volume.fits((240.0, 200.0, 10.0)))
        self.assertFalse(MAKERA_Z1.build_volume.fits((240.0, 200.0, 10.0)))


class TestFastenerParameters(unittest.TestCase):
    def test_planet_pin_follows_planet_bolt(self) -> None:
        default = SpurDifferentialGeometry()
        m4 = SpurDifferentialGeometry(planet_bolt=MetricThread.M4)
        self.assertAlmostEqual(default.planet_pin_diameter, 3.0)
        self.assertAlmostEqual(m4.planet_pin_diameter, 4.0)
        self.assertEqual(m4.problems(), [])

    def test_layout_holes_follow_fastener(self) -> None:
        default = DrivetrainLayout()
        m4 = DrivetrainLayout(fastener=MetricThread.M4)
        for side in PlateSide:
            _, default_holes = default.plate_features(side)
            _, m4_holes = m4.plate_features(side)
            self.assertEqual(len(default_holes), len(m4_holes))
            self.assertTrue(
                all(
                    h.radius == MetricThread.M3.spec.clearance_radius
                    for h in default_holes
                )
            )
            self.assertTrue(
                all(h.radius == MetricThread.M4.spec.clearance_radius for h in m4_holes)
            )
        self.assertEqual(m4.problems(), [])

    def test_engine_accepts_other_fastener(self) -> None:
        engine = EngineGeometry(fastener=MetricThread.M2_5)
        self.assertEqual(engine.problems(), [])
        self.assertEqual(
            len(engine.head_bolt_positions()),
            len(EngineGeometry().head_bolt_positions()),
        )


class TestTolerancesAreParameters(unittest.TestCase):
    def test_min_clearance_drives_layout_checks(self) -> None:
        self.assertEqual(DrivetrainLayout().problems(), [])
        strict = DrivetrainLayout(min_clearance=1000.0)
        self.assertNotEqual(strict.problems(), [])

    def test_engine_piston_parameters_are_independent(self) -> None:
        base = EngineGeometry()
        thick = EngineGeometry(piston_wall=3.0, ring_groove_depth=1.0)
        self.assertEqual(thick.problems(), [])
        self.assertEqual(base.bore, thick.bore)
        self.assertNotEqual(base.piston_wall, thick.piston_wall)


if __name__ == "__main__":
    unittest.main()
