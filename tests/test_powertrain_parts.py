import unittest
from typing import Tuple

import cadquery as cq

from efficio.measures import Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.powertrain.axles import HexWheelAdapter, PillowBlock
from efficio.objects.powertrain.bearings import BEARING_625, StandardBearing
from efficio.objects.powertrain.differential import (
    SpurDifferentialCarrierHalf,
    SpurDifferentialGeometry,
    planet_gear,
    ring_gear,
    sun_gear,
)
from efficio.objects.powertrain.engine import (
    ConnectingRod,
    CrankWeb,
    CylinderHead,
    EngineBlockHalf,
    EngineGeometry,
    Flywheel,
    Piston,
)
from efficio.objects.powertrain.gearbox import BearingPlate, PlateHole, PlateSeat
from efficio.objects.powertrain.gears import CompoundSpurGear, SpurGear
from efficio.objects.powertrain.layout import DrivetrainLayout, PlateSide
from efficio.objects.powertrain.profiles import d_profile
from efficio.objects.powertrain.shafts import Shaft, Standoff
from efficio.objects.powertrain.wheels import Rim, Tire
from efficio.objects.shapes import Shape

Bounds = Tuple[float, float, float, float, float, float]


def _solid(obj: EfficioObject) -> Tuple[Shape, Bounds, float]:
    shape = obj.shape()
    assert shape is not None
    assert shape.isValid()
    bounds = shape.bounds()
    assert bounds is not None
    volume = sum(
        v.Volume() for v in shape.workplane().vals() if isinstance(v, cq.Shape)
    )
    return shape, bounds, volume


def _size(bounds: Bounds) -> Tuple[float, float, float]:
    return (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])


class TestGears(unittest.TestCase):
    def test_spur_gear_envelope(self) -> None:
        gear = SpurGear(
            MetricModule.MODULE_1_5, 36, Millimeter(10), Millimeter(5), True
        )
        _, bounds, volume = _solid(gear)
        width, _, height = _size(bounds)
        self.assertAlmostEqual(height, 10.0, places=3)
        self.assertLessEqual(width, 2 * 28.5 + 0.01)
        self.assertGreater(width, 2 * 28.0)
        self.assertGreater(volume, 3.14159 * 25.125**2 * 10 * 0.95)
        self.assertLess(volume, 3.14159 * 28.5**2 * 10)

    def test_hub_extends_gear(self) -> None:
        gear = SpurGear(
            MetricModule.MODULE_1_5,
            20,
            Millimeter(6),
            Millimeter(5),
            False,
            PressureAngle.MODERN,
            hub_diameter=Millimeter(12),
            hub_length=Millimeter(4),
        )
        _, bounds, _ = _solid(gear)
        self.assertAlmostEqual(bounds[5] - bounds[2], 10.0, places=3)
        self.assertAlmostEqual(gear.length, 10.0)

    def test_d_bore_removes_less_than_round_bore(self) -> None:
        args = (MetricModule.MODULE_1_5, 12, Millimeter(10), Millimeter(8))
        _, _, d_volume = _solid(SpurGear(*args, True))
        _, _, round_volume = _solid(SpurGear(*args, False))
        self.assertGreater(d_volume, round_volume)

    def test_compound_gear_reuses_spur_gears(self) -> None:
        gear = CompoundSpurGear(
            MetricModule.MODULE_1_5,
            12,
            Millimeter(30),
            36,
            Millimeter(10),
            Millimeter(5),
        )
        self.assertIsInstance(gear.pinion, SpurGear)
        _, bounds, _ = _solid(gear)
        self.assertAlmostEqual(bounds[5] - bounds[2], 40.0, places=3)
        self.assertAlmostEqual(_size(bounds)[0], 57.0, delta=0.6)


class TestShafts(unittest.TestCase):
    def test_shaft_d_profile(self) -> None:
        self.assertAlmostEqual(max(x for x, _ in d_profile(5.0, 0.0)), 2.0)
        _, bounds, _ = _solid(Shaft(Millimeter(5), Millimeter(40), True))
        self.assertAlmostEqual(bounds[5] - bounds[2], 40.0, places=3)

    def test_standoff(self) -> None:
        _, bounds, _ = _solid(Standoff(Millimeter(48.5), Millimeter(7)))
        self.assertAlmostEqual(bounds[5] - bounds[2], 48.5, places=3)


class TestDifferentialParts(unittest.TestCase):
    def setUp(self) -> None:
        self.diff = SpurDifferentialGeometry()

    def test_gears_are_spur_gears_sized_from_geometry(self) -> None:
        diff = self.diff
        self.assertEqual(sun_gear(diff).teeth, diff.sun_teeth)
        self.assertTrue(sun_gear(diff).d_flat)
        self.assertAlmostEqual(
            sun_gear(diff).length, diff.sun_width + diff.sun_hub_length
        )
        self.assertAlmostEqual(planet_gear(diff).length, diff.planet_length)
        self.assertEqual(ring_gear(diff, 10.0).teeth, diff.ring_teeth)
        for gear in (sun_gear(diff), planet_gear(diff)):
            _solid(gear)

    def test_carrier_half(self) -> None:
        diff = self.diff
        _, bounds, _ = _solid(SpurDifferentialCarrierHalf(diff, Millimeter(20.5)))
        width, _, height = _size(bounds)
        self.assertAlmostEqual(width, 2 * diff.ring_tip_radius, delta=0.6)
        self.assertAlmostEqual(height, diff.drum_width / 2 + 20.5, places=3)

    def test_larger_differential_builds(self) -> None:
        diff = SpurDifferentialGeometry(sun_teeth=14, ring_teeth=52, sun_width=10.0)
        _, bounds, _ = _solid(SpurDifferentialCarrierHalf(diff, Millimeter(5)))
        self.assertAlmostEqual(_size(bounds)[0], 2 * diff.ring_tip_radius, delta=0.6)


class TestGearbox(unittest.TestCase):
    def test_layout_plates(self) -> None:
        layout = DrivetrainLayout()
        for side in PlateSide:
            seats, holes = layout.plate_features(side)
            plate = BearingPlate(Millimeter(layout.plate_thickness), seats, holes)
            _, bounds, _ = _solid(plate)
            self.assertAlmostEqual(bounds[5] - bounds[2], 8.0, places=3)
            self.assertLess(bounds[0], -42.0)
            self.assertGreater(bounds[3], 96.0)

    def test_generic_bearing_plate(self) -> None:
        plate = BearingPlate(
            Millimeter(6),
            [PlateSeat((0.0, 0.0), BEARING_625, 3.0)],
            [PlateHole((30.0, 0.0), 1.7)],
        )
        _, bounds, volume = _solid(plate)
        self.assertAlmostEqual(bounds[0], -(BEARING_625.seat_radius + 4.0), delta=0.05)
        self.assertAlmostEqual(bounds[3], 30.0 + 1.7 + 4.5, delta=0.05)
        solid = BearingPlate(
            Millimeter(6),
            [],
            [PlateHole((0.0, 0.0), 0.1, 12.0), PlateHole((30.0, 0.0), 0.1)],
        )
        self.assertLess(volume, _solid(solid)[2])

    def test_empty_plate_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BearingPlate(Millimeter(6), [], [])


class TestEngineParts(unittest.TestCase):
    def test_block_halves_split_on_crank_axis(self) -> None:
        for engine in (EngineGeometry(), EngineGeometry(cylinders=1)):
            with self.subTest(cylinders=engine.cylinders):
                _, upper, _ = _solid(EngineBlockHalf(engine, upper=True))
                _, lower, _ = _solid(EngineBlockHalf(engine, upper=False))
                self.assertAlmostEqual(upper[2], 0.0, places=3)
                self.assertAlmostEqual(upper[5], engine.deck_height, places=3)
                self.assertAlmostEqual(lower[5], 0.0, places=3)
                self.assertAlmostEqual(lower[2], -engine.block_half_width, places=3)
                self.assertAlmostEqual(upper[4] - upper[1], engine.block_length, 3)

    def test_rotating_parts_from_engine(self) -> None:
        engine = EngineGeometry(
            bore=26.0, stroke=24.0, rod_length=48.0, cylinder_spacing=34.0
        )
        _, web, _ = _solid(CrankWeb.from_engine(engine))
        self.assertAlmostEqual(web[3], engine.crank_throw + engine.web_pin_radius, 1)
        _, rod, _ = _solid(ConnectingRod.from_engine(engine))
        self.assertAlmostEqual(
            rod[4] - rod[1],
            engine.rod_length + engine.rod_big_end_radius + engine.rod_small_end_radius,
            delta=0.05,
        )
        _, piston, _ = _solid(Piston.from_engine(engine))
        self.assertLess(piston[3] - piston[0], engine.bore)
        self.assertAlmostEqual(piston[5], engine.piston_compression_height, 3)
        _, head, _ = _solid(CylinderHead(engine))
        self.assertAlmostEqual(head[5] - head[2], engine.head_thickness, 3)

    def test_flywheel(self) -> None:
        _, fly, _ = _solid(Flywheel(Millimeter(50), Millimeter(8), Millimeter(8), 4))
        self.assertAlmostEqual(fly[3] - fly[0], 50.0, delta=0.1)


class TestAxlesAndWheels(unittest.TestCase):
    def test_rim_tire_adapter(self) -> None:
        rim = Rim(Millimeter(80), Millimeter(30), Millimeter(12), Millimeter(8), 5)
        _, rim_bounds, _ = _solid(rim)
        self.assertAlmostEqual(rim_bounds[5] - rim_bounds[2], 30.0, places=3)
        self.assertAlmostEqual(rim_bounds[3] - rim_bounds[0], 84.0, delta=0.2)
        self.assertAlmostEqual(rim.tire_width(), 26.0)
        _, tire, _ = _solid(Tire(Millimeter(110), Millimeter(80), Millimeter(26), 24))
        self.assertAlmostEqual(tire[3] - tire[0], 110.0, delta=0.5)
        _, hex_adapter, _ = _solid(
            HexWheelAdapter(Millimeter(12), Millimeter(8), Millimeter(5))
        )
        self.assertAlmostEqual(hex_adapter[5] - hex_adapter[2], 8.0, places=3)

    def test_pillow_block_takes_any_standard_bearing(self) -> None:
        small = PillowBlock(
            Millimeter(5), StandardBearing.B625, Millimeter(15), Millimeter(10)
        )
        large = PillowBlock(
            Millimeter(8), StandardBearing.B608, Millimeter(20), Millimeter(10)
        )
        _, small_bounds, _ = _solid(small)
        _, large_bounds, _ = _solid(large)
        self.assertAlmostEqual(small_bounds[1], -15.0, places=3)
        self.assertAlmostEqual(large_bounds[1], -20.0, places=3)
        self.assertGreater(_size(large_bounds)[0], _size(small_bounds)[0])
