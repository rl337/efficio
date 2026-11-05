import math
import unittest

from efficio.objects.drivetrain_layout import DrivetrainLayout, Span
from efficio.objects.involute import distance


class TestDrivetrainLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = DrivetrainLayout()

    def test_default_layout_has_no_problems(self) -> None:
        self.assertEqual(self.layout.problems(), [])

    def test_reduction_ratio(self) -> None:
        self.assertAlmostEqual(self.layout.reduction_ratio, 11.5)

    def test_shaft_centres_come_from_pitch_radii(self) -> None:
        layout = self.layout
        idler_to_axle = distance(layout.idler_centre, layout.axle_centre)
        crank_to_idler = distance(layout.crank_centre, layout.idler_centre)
        self.assertAlmostEqual(idler_to_axle, 1.5 * (12 + 46) / 2)
        self.assertAlmostEqual(crank_to_idler, 1.5 * (12 + 36) / 2)

    def test_axle_height_matches_wheel_radius(self) -> None:
        self.assertAlmostEqual(self.layout.axle_centre[1], 55.0)

    def test_planet_pairs_mesh_with_each_other(self) -> None:
        layout = self.layout
        poses = layout.planet_poses(0.0, 0.0)
        p1 = next(p for p in poses if p.name == "P1.0")
        p2 = next(p for p in poses if p.name == "P2.0")
        self.assertAlmostEqual(distance(p1.centre, p2.centre), 1.5 * 12)
        for pose in poses:
            self.assertAlmostEqual(
                distance(pose.centre, layout.axle_centre), layout.planet_orbit_radius
            )

    def test_planets_overlap_only_in_mesh_zone(self) -> None:
        layout = self.layout
        poses = layout.planet_poses(0.0, 0.0)
        p1 = next(p for p in poses if p.name.startswith("P1"))
        p2 = next(p for p in poses if p.name.startswith("P2"))
        self.assertFalse(p1.span.overlaps(layout.sun_b))
        self.assertFalse(p2.span.overlaps(layout.sun_a))
        overlap = min(p1.span.end, p2.span.end) - max(p1.span.start, p2.span.start)
        self.assertGreaterEqual(overlap, 6.0)

    def test_both_planet_pairs_agree_on_right_sun_phase(self) -> None:
        layout = self.layout
        for carrier in (0.0, 7.0, 123.0):
            poses = layout.planet_poses(carrier, 0.0)
            pitch = 360.0 / layout.sun_teeth
            a = layout.sun_b_phase(poses, 0) % pitch
            b = layout.sun_b_phase(poses, 1) % pitch
            delta = min(abs(a - b), pitch - abs(a - b))
            self.assertAlmostEqual(delta, 0.0, places=6)

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

    def test_wheels_symmetric_about_differential(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            layout.left_wheel.centre + layout.right_wheel.centre,
            2 * layout.drum.centre,
        )
        self.assertAlmostEqual(layout.track_width, 288.0)

    def test_half_shafts_reach_the_wheel_adapters(self) -> None:
        layout = self.layout
        self.assertAlmostEqual(
            layout.left_half_shaft.start,
            layout.left_wheel.end - layout.hex_adapter_length,
        )
        self.assertAlmostEqual(
            layout.right_half_shaft.end,
            layout.right_wheel.start + layout.hex_adapter_length,
        )

    def test_engine_kinematics(self) -> None:
        layout = self.layout
        tdc = layout.engine_pose(90.0)
        self.assertAlmostEqual(
            tdc.wrist_pin_heights[0] - layout.crank_centre[1],
            layout.crank_throw + layout.rod_length,
        )
        # Twin is a 180 degree crank, so cylinder 1 is at BDC.
        self.assertAlmostEqual(
            tdc.wrist_pin_heights[1] - layout.crank_centre[1],
            layout.rod_length - layout.crank_throw,
        )
        self.assertAlmostEqual(tdc.rod_angles[0], 90.0)
        mid = layout.engine_pose(0.0)
        self.assertAlmostEqual(
            mid.rod_angles[0],
            180.0 - math.degrees(math.acos(layout.crank_throw / layout.rod_length)),
        )

    def test_piston_clears_head_at_tdc(self) -> None:
        layout = self.layout
        tdc = layout.engine_pose(90.0)
        crown = tdc.wrist_pin_heights[0] + layout.piston_compression_height
        self.assertLess(crown, layout.crank_centre[1] + layout.deck_height)

    def test_problems_detect_bad_designs(self) -> None:
        crowded = DrivetrainLayout(cylinder_spacing=12.0)
        self.assertTrue(crowded.problems())
        no_room = DrivetrainLayout(ring_teeth=38)
        self.assertTrue(no_room.problems())

    def test_span(self) -> None:
        span = Span(1.0, 4.0)
        self.assertAlmostEqual(span.length, 3.0)
        self.assertAlmostEqual(span.centre, 2.5)
        self.assertTrue(span.overlaps(Span(3.0, 5.0)))
        self.assertFalse(span.overlaps(Span(4.0, 5.0)))
