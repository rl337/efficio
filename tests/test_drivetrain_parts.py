import unittest
from typing import Tuple

import cadquery as cq

from efficio.measures import Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.drivetrain import (
    CompoundSpurGear,
    DifferentialCarrierHalf,
    DifferentialPlanet,
    DifferentialSun,
    GearboxPlate,
    PlateSide,
    Shaft,
    SpurGear,
    Standoff,
    d_profile,
)
from efficio.objects.drivetrain_layout import DrivetrainLayout
from efficio.objects.engine import (
    ConnectingRod,
    CrankWeb,
    CylinderHead,
    EngineBlockHalf,
    Flywheel,
    Piston,
)
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.shapes import Shape
from efficio.objects.wheels import HexWheelAdapter, PillowBlock, Rim, Tire

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
    return (
        bounds[3] - bounds[0],
        bounds[4] - bounds[1],
        bounds[5] - bounds[2],
    )


class TestGearParts(unittest.TestCase):
    def test_spur_gear_envelope(self) -> None:
        gear = SpurGear(
            MetricModule.MODULE_1_5,
            36,
            Millimeter(10),
            Millimeter(5),
            True,
            PressureAngle.HIGH_TORQUE,
        )
        _, bounds, volume = _solid(gear)
        width, length, height = _size(bounds)
        self.assertAlmostEqual(height, 10.0, places=3)
        self.assertLessEqual(width, 2 * 28.5 + 0.01)
        self.assertGreater(width, 2 * 28.0)
        # Between root disc and tip disc.
        self.assertGreater(volume, 3.14159 * 25.125**2 * 10 * 0.95)
        self.assertLess(volume, 3.14159 * 28.5**2 * 10)

    def test_d_bore_removes_less_than_round_bore(self) -> None:
        args = (MetricModule.MODULE_1_5, 12, Millimeter(10), Millimeter(8))
        _, _, d_volume = _solid(SpurGear(*args, True))
        _, _, round_volume = _solid(SpurGear(*args, False))
        self.assertGreater(d_volume, round_volume)

    def test_compound_gear_stacks_pinion_and_gear(self) -> None:
        gear = CompoundSpurGear(
            MetricModule.MODULE_1_5,
            12,
            Millimeter(30),
            36,
            Millimeter(10),
            Millimeter(5),
        )
        _, bounds, _ = _solid(gear)
        self.assertAlmostEqual(bounds[5] - bounds[2], 40.0, places=3)
        self.assertAlmostEqual(_size(bounds)[0], 57.0, delta=0.6)

    def test_shaft_d_profile(self) -> None:
        profile = d_profile(5.0, 0.0)
        self.assertAlmostEqual(max(x for x, _ in profile), 2.0)
        _, bounds, _ = _solid(Shaft(Millimeter(5), Millimeter(40), True))
        self.assertAlmostEqual(bounds[5] - bounds[2], 40.0, places=3)


class TestDifferentialParts(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = DrivetrainLayout()

    def test_carrier_half(self) -> None:
        layout = self.layout
        half = DifferentialCarrierHalf(layout, Millimeter(20.5))
        _, bounds, _ = _solid(half)
        width, length, height = _size(bounds)
        self.assertAlmostEqual(width, 2 * 36.0, delta=0.6)
        self.assertAlmostEqual(height, layout.drum.length / 2 + 20.5, places=3)

    def test_sun_and_planet(self) -> None:
        layout = self.layout
        _, sun_bounds, _ = _solid(DifferentialSun(layout))
        self.assertAlmostEqual(
            sun_bounds[5] - sun_bounds[2],
            layout.sun_width + layout.sun_hub_length,
            places=3,
        )
        _, planet_bounds, _ = _solid(DifferentialPlanet(layout))
        self.assertAlmostEqual(
            planet_bounds[5] - planet_bounds[2], layout.planet_length, places=3
        )

    def test_gearbox_plates(self) -> None:
        for side in PlateSide:
            _, bounds, _ = _solid(GearboxPlate(self.layout, side))
            self.assertAlmostEqual(bounds[5] - bounds[2], 8.0, places=3)
            self.assertLess(bounds[0], -42.0)
            self.assertGreater(bounds[3], 96.0)

    def test_standoff(self) -> None:
        _, bounds, _ = _solid(Standoff(Millimeter(48.5), Millimeter(7)))
        self.assertAlmostEqual(bounds[5] - bounds[2], 48.5, places=3)


class TestEngineParts(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = DrivetrainLayout()

    def test_block_halves_split_on_crank_axis(self) -> None:
        layout = self.layout
        _, upper, _ = _solid(EngineBlockHalf(layout, upper=True))
        _, lower, _ = _solid(EngineBlockHalf(layout, upper=False))
        self.assertAlmostEqual(upper[2], 0.0, places=3)
        self.assertAlmostEqual(upper[5], layout.deck_height, places=3)
        self.assertAlmostEqual(lower[5], 0.0, places=3)
        self.assertAlmostEqual(lower[2], -layout.block_half_width, places=3)
        self.assertAlmostEqual(upper[4] - upper[1], layout.engine_block.length, 3)

    def test_rotating_engine_parts(self) -> None:
        layout = self.layout
        _, web, _ = _solid(CrankWeb(layout))
        self.assertAlmostEqual(web[3], layout.crank_throw + layout.web_pin_radius, 1)
        _, rod, _ = _solid(ConnectingRod(layout))
        self.assertGreater(rod[4] - rod[1], layout.rod_length)
        _, piston, _ = _solid(Piston(layout))
        self.assertLess(piston[3] - piston[0], layout.bore)
        self.assertAlmostEqual(piston[5], layout.piston_compression_height, 3)
        _, head, _ = _solid(CylinderHead(layout))
        self.assertAlmostEqual(head[5] - head[2], layout.head_thickness, 3)
        flywheel = Flywheel(Millimeter(50), Millimeter(8), Millimeter(8), 4)
        _, fly, _ = _solid(flywheel)
        self.assertAlmostEqual(fly[3] - fly[0], 50.0, delta=0.1)


class TestWheelParts(unittest.TestCase):
    def test_rim_tire_adapter_pillow(self) -> None:
        _, rim, _ = _solid(
            Rim(Millimeter(80), Millimeter(30), Millimeter(12), Millimeter(8), 5)
        )
        self.assertAlmostEqual(rim[5] - rim[2], 30.0, places=3)
        self.assertAlmostEqual(rim[3] - rim[0], 84.0, delta=0.2)
        _, tire, _ = _solid(Tire(Millimeter(110), Millimeter(80), Millimeter(26), 24))
        self.assertAlmostEqual(tire[3] - tire[0], 110.0, delta=0.5)
        _, hex_adapter, _ = _solid(
            HexWheelAdapter(Millimeter(12), Millimeter(8), Millimeter(5))
        )
        self.assertAlmostEqual(hex_adapter[5] - hex_adapter[2], 8.0, places=3)
        _, pillow, _ = _solid(
            PillowBlock(
                Millimeter(5),
                Millimeter(16),
                Millimeter(5),
                Millimeter(15),
                Millimeter(10),
            )
        )
        self.assertAlmostEqual(pillow[1], -15.0, places=3)
