import math
import unittest

from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.differential.geometry import SpurDifferentialGeometry
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.layout import DrivetrainLayout, PlateSide
from efficio.objects.powertrain.planar import distance


class TestEngineGeometry(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EngineGeometry()

    def test_default_engine_is_sound(self) -> None:
        self.assertEqual(self.engine.problems(), [])

    def test_other_cylinder_counts_are_sound(self) -> None:
        for cylinders in (1, 3, 4):
            with self.subTest(cylinders=cylinders):
                self.assertEqual(EngineGeometry(cylinders=cylinders).problems(), [])

    def test_bigger_engine_is_sound(self) -> None:
        engine = EngineGeometry(
            bore=30.0, stroke=26.0, rod_length=52.0, cylinder_spacing=40.0
        )
        self.assertEqual(engine.problems(), [])
        self.assertGreater(engine.block_half_width, self.engine.block_half_width)

    def test_bolt_patterns_follow_the_bore(self) -> None:
        engine = self.engine
        self.assertIn((14.0, engine.cylinder_y(0) + 10.0), engine.head_bolt_positions())
        self.assertEqual(len(engine.head_bolt_positions()), 4 * engine.cylinders)
        self.assertEqual(
            engine.flange_bolt_offsets(),
            [(-12.0, -15.0), (12.0, -15.0), (-12.0, 20.0), (12.0, 20.0)],
        )
        self.assertEqual(len(engine.split_bolt_positions()), 4)
        wide = EngineGeometry(bore=30.0, cylinder_spacing=40.0)
        self.assertGreater(
            wide.head_bolt_positions()[1][0], engine.head_bolt_positions()[1][0]
        )

    def test_throws_are_evenly_spaced(self) -> None:
        triple = EngineGeometry(cylinders=3)
        self.assertEqual(
            [triple.throw_angle(i, 10.0) for i in range(3)], [10.0, 130.0, 250.0]
        )

    def test_kinematics(self) -> None:
        engine = self.engine
        tdc = engine.pose(90.0)
        self.assertAlmostEqual(
            tdc.wrist_pin_heights[0], engine.crank_throw + engine.rod_length
        )
        # The twin is a 180 degree crank, so cylinder 1 is at BDC.
        self.assertAlmostEqual(
            tdc.wrist_pin_heights[1], engine.rod_length - engine.crank_throw
        )
        self.assertAlmostEqual(tdc.rod_angles[0], 90.0)
        mid = engine.pose(0.0)
        self.assertAlmostEqual(
            mid.rod_angles[0],
            180.0 - math.degrees(math.acos(engine.crank_throw / engine.rod_length)),
        )
        crown = tdc.wrist_pin_heights[0] + engine.piston_compression_height
        self.assertLess(crown, engine.deck_height)

    def test_rod_sweep_needs_crankcase_relief(self) -> None:
        class NoRelief(EngineGeometry):
            @property
            def crankcase_relief_half_width(self) -> float:
                return self.bore / 2.0

        self.assertEqual(self.engine.rod_clearance_problems(), [])
        self.assertTrue(NoRelief().rod_clearance_problems())

    def test_bad_engines_are_flagged(self) -> None:
        self.assertTrue(EngineGeometry(cylinder_spacing=12.0).problems())
        self.assertTrue(EngineGeometry(rod_length=18.0).problems())
        self.assertTrue(EngineGeometry(end_wall=6.0).problems())


class TestDifferentialGeometry(unittest.TestCase):
    def setUp(self) -> None:
        self.diff = SpurDifferentialGeometry()

    def test_default_differential_is_sound(self) -> None:
        self.assertEqual(self.diff.problems(), [])

    def test_planet_pairs_mesh(self) -> None:
        diff = self.diff
        poses = diff.planet_poses((0.0, 0.0), 0.0, 0.0)
        p1 = next(p for p in poses if p.name == "P1.0")
        p2 = next(p for p in poses if p.name == "P2.0")
        self.assertAlmostEqual(distance(p1.centre, p2.centre), 1.5 * 12)
        for pose in poses:
            self.assertAlmostEqual(
                distance(pose.centre, (0.0, 0.0)), diff.planet_orbit_radius
            )
        self.assertFalse(p1.span.overlaps(diff.sun_b))
        self.assertFalse(p2.span.overlaps(diff.sun_a))

    def test_both_pairs_agree_on_right_sun_phase(self) -> None:
        diff = self.diff
        pitch = 360.0 / diff.sun_teeth
        for carrier in (0.0, 7.0, 123.0):
            poses = diff.planet_poses((3.0, 4.0), carrier, 0.0)
            a = diff.sun_b_phase((3.0, 4.0), poses, 0) % pitch
            b = diff.sun_b_phase((3.0, 4.0), poses, 1) % pitch
            self.assertAlmostEqual(min(abs(a - b), pitch - abs(a - b)), 0.0, 6)

    def test_carrier_angles_are_mirror_symmetric(self) -> None:
        angles = sorted(round(a % 360, 6) for _, a in self.diff.planet_carrier_angles())
        mirrored = sorted(
            round(-a % 360, 6) for _, a in self.diff.planet_carrier_angles()
        )
        self.assertEqual(angles, mirrored)

    def test_bad_differentials_are_flagged(self) -> None:
        self.assertTrue(SpurDifferentialGeometry(planet_pairs=3).problems())
        self.assertTrue(SpurDifferentialGeometry(ring_teeth=38).problems())
        self.assertTrue(SpurDifferentialGeometry(sun_teeth=13).problems())

    def test_larger_differential_is_sound(self) -> None:
        diff = SpurDifferentialGeometry(
            sun_teeth=14, planet_teeth=12, ring_teeth=52, sun_width=10.0
        )
        self.assertEqual(diff.problems(), [])
        self.assertGreater(diff.drum_width, self.diff.drum_width)


class TestDrivetrainLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = DrivetrainLayout()

    def test_default_layout_has_no_problems(self) -> None:
        self.assertEqual(self.layout.problems(), [])

    def test_reduction_ratio(self) -> None:
        self.assertAlmostEqual(self.layout.reduction_ratio, 11.5)

    def test_shaft_centres_come_from_pitch_radii(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            distance(layout.idler_centre, layout.axle_centre), 1.5 * (12 + 46) / 2
        )
        self.assertAlmostEqual(
            distance(layout.crank_centre, layout.idler_centre), 1.5 * (12 + 36) / 2
        )
        self.assertAlmostEqual(layout.axle_centre[1], 55.0)

    def test_axial_stack_is_ordered(self) -> None:
        layout = self.layout
        stack = [
            layout.plate_left,
            layout.drum,
            layout.stage_plane,
            layout.plate_right,
            layout.engine_block,
            layout.flywheel,
            layout.right_wheel,
        ]
        for before, after in zip(stack, stack[1:]):
            self.assertLessEqual(before.end, after.start)

    def test_world_spans_shift_subsystem_spans(self) -> None:
        layout = self.layout
        self.assertEqual(
            layout.sun_a, layout.differential.sun_a.shifted(layout.carrier_offset)
        )
        self.assertAlmostEqual(
            layout.cylinder_y(1) - layout.cylinder_y(0),
            layout.engine.cylinder_spacing,
        )
        self.assertAlmostEqual(layout.engine_block.start, layout.plate_right.end)

    def test_wheels_and_half_shafts(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            layout.left_wheel.centre + layout.right_wheel.centre,
            2 * layout.drum.centre,
        )
        self.assertAlmostEqual(layout.track_width, 288.0)
        self.assertAlmostEqual(
            layout.left_half_shaft.start,
            layout.left_wheel.end - layout.hex_adapter_length,
        )
        self.assertAlmostEqual(
            layout.right_half_shaft.end,
            layout.right_wheel.start + layout.hex_adapter_length,
        )

    def test_plate_features(self) -> None:
        left_seats, left_holes = self.layout.plate_features(PlateSide.LEFT)
        right_seats, right_holes = self.layout.plate_features(PlateSide.RIGHT)
        self.assertEqual(len(left_seats), 3)
        self.assertEqual(len(right_seats), 2)
        self.assertEqual(len(left_holes), 4)
        self.assertEqual(len(right_holes), 4 + 1 + 4)
        # Right plate faces +y, so its z coordinates are mirrored.
        self.assertAlmostEqual(right_seats[0].centre[1], -left_seats[0].centre[1])

    def test_variant_layouts_are_sound(self) -> None:
        variants = [
            DrivetrainLayout(engine=EngineGeometry(cylinders=1)),
            DrivetrainLayout(engine=EngineGeometry(cylinders=3)),
            DrivetrainLayout(crank_pinion_teeth=14, idler_gear_teeth=34),
            DrivetrainLayout(
                differential=SpurDifferentialGeometry(ring_teeth=50),
                wheel_diameter=120.0,
                rim_diameter=86.0,
            ),
            DrivetrainLayout(axle_bearing=StandardBearing.B688),
        ]
        for layout in variants:
            with self.subTest(layout=layout):
                self.assertEqual(layout.problems(), [])

    def test_ratio_follows_tooth_counts(self) -> None:
        layout = DrivetrainLayout(crank_pinion_teeth=14, idler_gear_teeth=34)
        self.assertAlmostEqual(layout.reduction_ratio, (34 / 14) * (46 / 12))

    def test_bad_layouts_are_flagged(self) -> None:
        self.assertTrue(DrivetrainLayout(wheel_diameter=60.0).problems())
        self.assertTrue(
            DrivetrainLayout(engine=EngineGeometry(cylinder_spacing=12)).problems()
        )
