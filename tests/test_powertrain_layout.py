import math
import unittest

from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.differential.geometry import SpurDifferentialGeometry
from efficio.objects.powertrain.dowels import StandardDowel
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.layout import AxleStock, DrivetrainLayout, PlateSide
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

    def test_standard_crank_layouts(self) -> None:
        def offsets(n: int) -> list[float]:
            return EngineGeometry(cylinders=n).throw_offsets()

        self.assertEqual(offsets(1), [0.0])
        self.assertEqual(offsets(3), [0.0, 240.0, 120.0])
        self.assertEqual(offsets(4), [0.0, 180.0, 180.0, 0.0])
        self.assertEqual(offsets(6), [0.0, 120.0, 240.0, 240.0, 120.0, 0.0])
        self.assertAlmostEqual(EngineGeometry().throw_angle(1, 10.0), 190.0)

    def test_kinematics(self) -> None:
        engine = self.engine
        tdc = engine.pose(90.0)
        self.assertAlmostEqual(
            tdc.wrist_pin_heights[0], engine.crank_throw + engine.rod_length
        )
        # Flat-plane inline-4: cylinder 2 (index 1) is at BDC when 1 is at TDC.
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
        self.assertEqual(self.layout.engine.cylinders, 4)

    def test_reduction_ratio(self) -> None:
        self.assertAlmostEqual(self.layout.reduction_ratio, (48 / 12) * (46 / 16))

    def test_shaft_centres_come_from_pitch_radii(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            distance(layout.idler_centre, layout.axle_centre), 1.5 * (24 + 46) / 2
        )
        self.assertAlmostEqual(
            distance(layout.idler_centre, layout.input_centre), 1.5 * (16 + 24) / 2
        )
        self.assertAlmostEqual(layout.axle_centre[1], 55.0)
        self.assertAlmostEqual(layout.input_centre[1], layout.crank_height)

    def test_engine_sits_above_the_gearbox_and_extends_backward(self) -> None:
        layout = self.layout
        x0, z0, x1, _ = layout.engine_block_box
        self.assertLess(x0, 0.0)  # behind the axle
        self.assertGreater(x1, 0.0)  # over the axle
        self.assertGreater(z0, layout.axle_height + layout.ring_tip_radius)
        span = layout.engine_block_span
        self.assertGreater(span.start, layout.plate_left.end)
        self.assertLess(span.end, layout.plate_right.start)

    def test_cylinder_count_changes_length_not_track(self) -> None:
        tracks = set()
        lengths = []
        for cylinders in (1, 2, 3, 4, 6):
            layout = DrivetrainLayout(engine=EngineGeometry(cylinders=cylinders))
            self.assertEqual(layout.problems(), [], cylinders)
            tracks.add(round(layout.track_width, 6))
            box = layout.engine_block_box
            lengths.append(box[2] - box[0])
        self.assertEqual(len(tracks), 1)
        self.assertEqual(lengths, sorted(lengths))

    def test_engine_frame_maps_crank_to_world_x(self) -> None:
        layout = self.layout
        frame = layout.engine_frame()
        front = frame.to_world((0.0, 0.0, 0.0))
        rear = frame.to_world((0.0, 100.0, 0.0))
        side = frame.to_world((10.0, 0.0, 0.0))
        self.assertAlmostEqual(front[0], layout.engine_front)
        self.assertAlmostEqual(rear[0], layout.engine_front - 100.0)
        self.assertAlmostEqual(side[1], layout.crank_y + 10.0)
        self.assertAlmostEqual(front[2], layout.crank_height)

    def test_crown_and_pinion_geometry(self) -> None:
        layout = self.layout
        crown = layout.crown
        self.assertEqual(crown.problems(), [])
        span = layout.crank_pinion_span
        nx = layout.input_centre[0]
        self.assertLess(span.start, nx - crown.outer_radius)
        self.assertGreater(span.end, nx - crown.inner_radius)
        pitch_plane = layout.crown_span.end - crown.addendum
        self.assertAlmostEqual(layout.crank_y - pitch_plane, crown.pinion_pitch_radius)

    def test_axial_stack(self) -> None:
        layout = self.layout
        self.assertLessEqual(layout.plate_left.end, layout.drum.start)
        self.assertLessEqual(layout.crown_span.end, layout.stage_plane.start)
        self.assertLessEqual(layout.drum.start, layout.stage_plane.start)
        self.assertLessEqual(layout.stage_plane.end, layout.drum.end)
        self.assertLessEqual(layout.drum.end, layout.plate_right.start)
        for span in layout.engine_mount_spans():
            self.assertGreater(span.length, 1.0)

    def test_wheels_and_half_shafts(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            layout.left_wheel.centre + layout.right_wheel.centre,
            2 * layout.drum.centre,
        )
        self.assertAlmostEqual(layout.track_width, layout.min_track_width)
        self.assertAlmostEqual(
            layout.left_half_shaft.start,
            layout.left_wheel.end - layout.hex_adapter_length,
        )
        self.assertAlmostEqual(
            layout.right_half_shaft.end,
            layout.right_wheel.start + layout.hex_adapter_length,
        )

    def test_standoffs_and_mounts(self) -> None:
        layout = self.layout
        self.assertEqual(len(layout.standoff_centres()), 4)
        mounts = layout.engine_mount_centres()
        self.assertEqual(len(mounts), 2)
        for x, z in mounts:
            self.assertLess(x, layout.engine_front)
            self.assertGreater(z, layout.crank_height)

    def test_plate_features(self) -> None:
        left_seats, left_holes = self.layout.plate_features(PlateSide.LEFT)
        right_seats, right_holes = self.layout.plate_features(PlateSide.RIGHT)
        self.assertEqual(len(left_seats), 3)
        self.assertEqual(len(right_seats), 3)
        self.assertEqual(len(left_holes), 4 + 2)
        self.assertEqual(len(right_holes), 4 + 2)
        # Right plate faces +y, so its z coordinates are mirrored.
        self.assertAlmostEqual(right_seats[0].centre[1], -left_seats[0].centre[1])

    def test_gear_phases_follow_the_crank(self) -> None:
        layout = self.layout
        a = layout.gear_phases(0.0)
        b = layout.gear_phases(5.0)
        self.assertAlmostEqual(b["crank"], 5.0)
        pitch = 360.0 / layout.crown_teeth
        step = 5.0 * layout.crank_pinion_teeth / layout.crown_teeth
        self.assertAlmostEqual((b["crown"] - a["crown"]) % pitch, step % pitch)

    def test_variant_layouts_are_sound(self) -> None:
        variants = [
            DrivetrainLayout(engine=EngineGeometry(cylinders=1)),
            DrivetrainLayout(engine=EngineGeometry(cylinders=6)),
            DrivetrainLayout(
                differential=SpurDifferentialGeometry(ring_teeth=50),
                wheel_diameter=120.0,
                rim_diameter=86.0,
            ),
            DrivetrainLayout(pillow_centre_height=20.0, hex_across_flats=14.0),
            DrivetrainLayout(min_track_width=300.0),
        ]
        for layout in variants:
            with self.subTest(layout=layout):
                self.assertEqual(layout.problems(), [])

    def test_bad_layouts_are_flagged(self) -> None:
        self.assertTrue(DrivetrainLayout(wheel_diameter=60.0).problems())
        self.assertTrue(
            DrivetrainLayout(engine=EngineGeometry(cylinder_spacing=12)).problems()
        )
        self.assertTrue(DrivetrainLayout(crown_teeth=36).problems())
        self.assertTrue(DrivetrainLayout(engine_mount_gap=0.5).problems())


class TestDowels(unittest.TestCase):
    def test_catalogue_matches_inch_sizes(self) -> None:
        self.assertAlmostEqual(StandardDowel.D_1_4.spec.diameter, 6.35)
        self.assertAlmostEqual(StandardDowel.D_3_8.spec.diameter, 9.525)
        self.assertAlmostEqual(StandardDowel.D_1_4.spec.stock_lengths[0], 914.4)
        self.assertIn("5980552", StandardDowel.D_1_4.spec.description())

    def test_stock_pieces(self) -> None:
        dowel = StandardDowel.D_1_4.spec
        self.assertEqual(dowel.stock_pieces([140.0, 140.0]), 1)
        self.assertEqual(dowel.stock_pieces([500.0, 500.0]), 2)
        with self.assertRaises(ValueError):
            dowel.stock_pieces([1000.0])

    def test_dowel_axle_layout_is_sound(self) -> None:
        layout = DrivetrainLayout.with_dowel_axles()
        self.assertEqual(layout.problems(), [])
        self.assertTrue(layout.dowel_axles)
        self.assertAlmostEqual(layout.axle_diameter, 6.35)
        self.assertEqual(layout.axle_bearing, StandardBearing.R4)
        self.assertEqual(layout.carrier_bearing, StandardBearing.B6801)
        self.assertAlmostEqual(layout.differential.hub_diameter, 12.0)

    def test_dowel_runs_through_the_wheel_hub(self) -> None:
        steel = DrivetrainLayout()
        dowel = DrivetrainLayout.with_dowel_axles()
        self.assertAlmostEqual(
            dowel.right_half_shaft.end, dowel.right_wheel.start + dowel.rim_hub_length
        )
        self.assertGreater(dowel.right_half_shaft.length, steel.right_half_shaft.length)
        self.assertGreater(dowel.rim_axle_bore, dowel.axle_diameter)

    def test_cross_pins_sit_inside_their_shafts(self) -> None:
        layout = DrivetrainLayout.with_dowel_axles()
        pins = layout.axle_cross_pins()
        self.assertEqual(
            set(pins), {"sun_left", "sun_right", "wheel_left", "wheel_right"}
        )
        for name, y in pins.items():
            span = (
                layout.left_half_shaft
                if name.endswith("left")
                else layout.right_half_shaft
            )
            self.assertGreater(y - span.start, 3.0, name)
            self.assertGreater(span.end - y, 3.0, name)
        self.assertEqual(DrivetrainLayout().axle_cross_pins(), {})

    def test_larger_dowels_need_a_larger_hex(self) -> None:
        crowded = DrivetrainLayout.with_dowel_axles(StandardDowel.D_5_16)
        self.assertIn("hex adapter too small for the dowel", crowded.problems())
        roomy = DrivetrainLayout.with_dowel_axles(
            StandardDowel.D_5_16, hex_across_flats=14.0
        )
        self.assertEqual(roomy.problems(), [])

    def test_unsupported_dowel_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DrivetrainLayout.with_dowel_axles(StandardDowel.D_1)

    def test_mismatched_axle_settings_flagged(self) -> None:
        bad = DrivetrainLayout(axle_stock=AxleStock.WOOD_DOWEL)
        problems = bad.problems()
        self.assertIn("dowel axles need a cross-pin drive", problems)
        self.assertIn("differential is not bored for the dowel", problems)

    def test_axle_bearing_must_suit_the_axle(self) -> None:
        loose = DrivetrainLayout(axle_bearing=StandardBearing.B688)
        self.assertIn("axle bearing bore much larger than the axle", loose.problems())
