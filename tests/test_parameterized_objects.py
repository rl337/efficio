"""Solid-building tests for objects refactored by the parameterized-objects
skill: each is built with the standard values and a non-default set."""

import unittest
from typing import Tuple

import cadquery as cq

from efficio.measures import Millimeter
from efficio.objects import EfficioObject
from efficio.objects.enclosures import Button, RoundedBox
from efficio.objects.fasteners import (
    Bolt,
    BoltChannel,
    HexNut,
    M3Bolt,
    M3HexNut,
    MetricThread,
)
from efficio.objects.gears import (
    AbstractCogwheel,
    CrownGear,
    GearSystem,
    MetricModule,
    PressureAngle,
    SphericalGear,
    SpurGear,
)
from efficio.objects.molds import MoldFeatures, MoldPolarity, MoldTooling
from efficio.objects.powertrain.axles.pillow_block import PillowBlock
from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.gears import (
    DRIVETRAIN_GEAR_SYSTEM,
    DrivetrainCrownGear,
    DrivetrainSpurGear,
)
from efficio.objects.vessels import TriangularFlaskVase

Bounds = Tuple[float, float, float, float, float, float]


def _bounds(obj: EfficioObject) -> Bounds:
    shape = obj.shape()
    assert shape is not None
    bounds = shape.bounds()
    assert bounds is not None
    result: Bounds = bounds
    return result


def _volume(obj: EfficioObject) -> float:
    shape = obj.shape()
    assert shape is not None
    return sum(v.Volume() for v in shape.workplane().vals() if isinstance(v, cq.Shape))


def _size(bounds: Bounds) -> Tuple[float, float, float]:
    """Extents sorted largest first, so tests don't depend on orientation."""
    a, b, c = sorted(
        (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2]),
        reverse=True,
    )
    return (a, b, c)


class TestFasteners(unittest.TestCase):
    def test_m3_bolt_is_a_bolt_with_m3_thread(self) -> None:
        standard = _bounds(M3Bolt(Millimeter(10), False))
        generic = _bounds(Bolt(MetricThread.M3, Millimeter(10), False))
        for a, b in zip(standard, generic):
            self.assertAlmostEqual(a, b, places=4)

    def test_bolt_size_follows_thread(self) -> None:
        for thread in (MetricThread.M3, MetricThread.M5):
            spec = thread.spec
            with self.subTest(thread=thread.name):
                height, width, depth = _size(
                    _bounds(Bolt(thread, Millimeter(12), False))
                )
                self.assertAlmostEqual(width, spec.head_diameter, delta=0.05)
                self.assertAlmostEqual(depth, spec.head_diameter, delta=0.05)
                self.assertAlmostEqual(height, 12 + spec.head_height, delta=0.05)

    def test_nut_size_follows_thread(self) -> None:
        m3 = _size(_bounds(M3HexNut(False)))
        m4 = _size(_bounds(HexNut(MetricThread.M4, False)))
        self.assertGreater(m4[0], m3[0])
        self.assertAlmostEqual(m4[2], MetricThread.M4.spec.nut_height, delta=0.05)

    def test_bolt_channel_cut_is_valid_for_other_threads(self) -> None:
        cut = BoltChannel(MetricThread.M4, Millimeter(20)).cut()
        self.assertIsNotNone(cut)
        assert cut is not None
        self.assertTrue(cut.isValid())


class TestEnclosures(unittest.TestCase):
    def test_button_shaft_sits_on_head(self) -> None:
        width, _, height = _size(
            _bounds(
                Button(
                    Millimeter(3), Millimeter(12), Millimeter(5), Millimeter(4), False
                )
            )
        )
        self.assertAlmostEqual(width, 12, delta=0.05)
        self.assertAlmostEqual(height, 8, delta=0.05)

    def test_rounded_box_accepts_other_fastener(self) -> None:
        for thread in (MetricThread.M3, MetricThread.M4):
            with self.subTest(thread=thread.name):
                box = RoundedBox(
                    Millimeter(60), Millimeter(40), Millimeter(25), fastener=thread
                )
                shape = box.shape()
                self.assertIsNotNone(shape)
                assert shape is not None
                self.assertTrue(shape.isValid())


class TestVessels(unittest.TestCase):
    def test_flask_rejects_bad_body_fraction(self) -> None:
        for fraction in (0.0, 1.0, -0.2):
            with self.subTest(fraction=fraction):
                with self.assertRaises(ValueError):
                    TriangularFlaskVase(
                        Millimeter(40),
                        Millimeter(80),
                        Millimeter(30),
                        Millimeter(10),
                        body_fraction=fraction,
                    )

    def test_flask_builds_with_other_body_fraction(self) -> None:
        vase = TriangularFlaskVase(
            Millimeter(40), Millimeter(80), Millimeter(30), Millimeter(10), 0.6
        )
        self.assertAlmostEqual(_size(_bounds(vase))[0], 80, delta=0.5)


class TestGears(unittest.TestCase):
    def test_involute_gears_are_cogwheels(self) -> None:
        spur = SpurGear(MetricModule.MODULE_1, 20, Millimeter(5), Millimeter(5), False)
        crown = CrownGear(
            MetricModule.MODULE_1, 48, 12, Millimeter(4), Millimeter(5), False
        )
        for gear in (spur, crown):
            self.assertIsInstance(gear, AbstractCogwheel)
        self.assertEqual(spur.get_tooth_count(), 20)
        # Tip radius of a standard spur gear is (teeth + 2) * module / 2.
        self.assertAlmostEqual(spur.get_maximum_radius().value(), 11.0, places=6)
        self.assertAlmostEqual(_size(_bounds(spur))[0], 22.0, delta=0.1)

    def test_drivetrain_spur_gear_is_spur_gear_on_drivetrain_system(self) -> None:
        system = DRIVETRAIN_GEAR_SYSTEM
        fixed = DrivetrainSpurGear(16, Millimeter(10), Millimeter(5))
        general = SpurGear(
            system.module,
            16,
            Millimeter(10),
            Millimeter(5),
            True,
            system.pressure_angle,
            backlash=Millimeter(system.backlash),
        )
        self.assertEqual(fixed.geometry(), general.geometry())
        self.assertAlmostEqual(_volume(fixed), _volume(general), places=3)

    def test_drivetrain_gears_accept_other_system(self) -> None:
        fine = GearSystem(MetricModule.MODULE_1, PressureAngle.MODERN, 0.1)
        spur = DrivetrainSpurGear(20, Millimeter(5), Millimeter(5), system=fine)
        crown = DrivetrainCrownGear(48, 12, Millimeter(4), Millimeter(5), system=fine)
        self.assertAlmostEqual(spur.geometry().module, 1.0)
        self.assertAlmostEqual(crown.geometry().pressure_angle_degrees, 20.0)
        self.assertEqual(crown.geometry().problems(), [])
        self.assertTrue(crown.shape() is not None)


class TestParameterizedParts(unittest.TestCase):
    def test_spherical_gear_tooth_height_is_a_parameter(self) -> None:
        # The tip radius is a hard envelope, so deeper teeth remove material.
        shallow = SphericalGear(Millimeter(20), 12)
        deep = SphericalGear(Millimeter(20), 12, tooth_height_ratio=0.2)
        self.assertAlmostEqual(_size(_bounds(deep))[0], 40.0, delta=0.1)
        self.assertLess(_volume(deep), _volume(shallow))

    def test_pillow_block_with_other_fastener_and_wall(self) -> None:
        default = PillowBlock(
            Millimeter(8), StandardBearing.B608, Millimeter(20), Millimeter(10)
        )
        wide = PillowBlock(
            Millimeter(8),
            StandardBearing.B608,
            Millimeter(20),
            Millimeter(10),
            boss_wall=Millimeter(5),
            fastener=MetricThread.M4,
        )
        self.assertGreater(wide.boss_radius(), default.boss_radius())
        self.assertGreater(sum(_size(_bounds(wide))), sum(_size(_bounds(default))))

    def test_mold_features_are_parameters(self) -> None:
        tooling = MoldTooling(
            master=SphericalGear(Millimeter(15), 12),
            polarity=MoldPolarity.NEGATIVE,
            features=MoldFeatures(
                registration_pin_radius=3.0, fastener=MetricThread.M4
            ),
        )
        for section in tooling.cottle_sections():
            self.assertTrue(section.geometry.isValid())


if __name__ == "__main__":
    unittest.main()
