import math
import unittest

from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    involute_function,
    mesh_phase,
)
from efficio.objects.powertrain.planar import (
    Span,
    convex_hull,
    densify,
    distance,
    hull_of_circles,
)


class TestInvoluteGeometry(unittest.TestCase):
    def test_standard_radii(self) -> None:
        gear = InvoluteGearGeometry(module=1.5, teeth=36, pressure_angle_degrees=20)
        self.assertAlmostEqual(gear.pitch_radius, 27.0)
        self.assertAlmostEqual(gear.tip_radius, 28.5)
        self.assertAlmostEqual(gear.root_radius, 25.125)
        self.assertAlmostEqual(gear.base_radius, 27.0 * math.cos(math.radians(20)))

    def test_involute_function(self) -> None:
        self.assertAlmostEqual(involute_function(0.0), 0.0)
        self.assertAlmostEqual(
            involute_function(math.radians(20)), 0.014904383867336446
        )

    def test_outline_stays_between_root_and_tip(self) -> None:
        gear = InvoluteGearGeometry(module=1.5, teeth=12)
        outline = gear.outline()
        radii = [math.hypot(x, y) for x, y in outline]
        self.assertGreaterEqual(min(radii), gear.root_radius - 1e-9)
        self.assertLessEqual(max(radii), gear.tip_radius + 1e-9)

    def test_outline_has_one_tip_per_tooth(self) -> None:
        gear = InvoluteGearGeometry(module=1.5, teeth=46)
        tips = [
            (x, y)
            for x, y in gear.outline()
            if abs(math.hypot(x, y) - gear.tip_radius) < 1e-6
        ]
        # Each tooth contributes the two flank end points and the tip centre.
        self.assertEqual(len(tips), 3 * 46)

    def test_tooth_zero_is_centred_on_x(self) -> None:
        gear = InvoluteGearGeometry(module=1.5, teeth=12)
        self.assertIn((gear.tip_radius, 0.0), gear.outline())

    def test_backlash_thins_teeth(self) -> None:
        tight = InvoluteGearGeometry(module=1.5, teeth=20, backlash=0.0)
        loose = InvoluteGearGeometry(module=1.5, teeth=20, backlash=0.3)
        radius = tight.pitch_radius
        self.assertLess(
            loose.half_thickness_angle(radius), tight.half_thickness_angle(radius)
        )
        self.assertAlmostEqual(
            2 * radius * tight.half_thickness_angle(radius), math.pi * 1.5 / 2
        )

    def test_twelve_teeth_at_25_degrees_has_a_tip_land(self) -> None:
        gear = InvoluteGearGeometry(module=1.5, teeth=12, pressure_angle_degrees=25)
        self.assertGreater(gear.tip_land_width(), 0.3)

    def test_pointed_teeth_rejected(self) -> None:
        gear = InvoluteGearGeometry(module=1.0, teeth=8, backlash=0.9)
        with self.assertRaises(ValueError):
            gear.outline()

    def test_invalid_gears_rejected(self) -> None:
        with self.assertRaises(ValueError):
            InvoluteGearGeometry(module=1.0, teeth=4)
        with self.assertRaises(ValueError):
            InvoluteGearGeometry(module=0.0, teeth=20)


class TestMeshing(unittest.TestCase):
    def test_centre_distance(self) -> None:
        self.assertAlmostEqual(centre_distance(1.5, 12, 36), 36.0)

    def test_driven_gap_faces_driver_tooth(self) -> None:
        # Driver tooth points straight at the driven gear (alpha = 0); the
        # driven gear must present a gap (half a pitch off a tooth) at 180.
        phase = mesh_phase((0, 0), 0.0, 12, (36, 0), 36)
        self.assertAlmostEqual(phase, 5.0)

    def test_phase_follows_gear_ratio(self) -> None:
        base = mesh_phase((0, 0), 0.0, 12, (36, 0), 36)
        turned = mesh_phase((0, 0), 6.0, 12, (36, 0), 36)
        self.assertAlmostEqual((base - turned) % 10.0, 2.0)

    def test_phase_is_normalised(self) -> None:
        phase = mesh_phase((0, 0), 1234.0, 12, (0, 36), 36)
        self.assertGreaterEqual(phase, 0.0)
        self.assertLess(phase, 10.0)


class TestPlanarHelpers(unittest.TestCase):
    def test_convex_hull_of_square_with_interior_point(self) -> None:
        hull = convex_hull([(0, 0), (2, 0), (2, 2), (0, 2), (1, 1)])
        self.assertEqual(len(hull), 4)
        self.assertNotIn((1.0, 1.0), hull)

    def test_distance(self) -> None:
        self.assertAlmostEqual(distance((0, 0), (3, 4)), 5.0)

    def test_hull_of_circles_covers_both_circles(self) -> None:
        hull = hull_of_circles([((0, 0), 2.0), ((10, 0), 1.0)])
        self.assertAlmostEqual(min(x for x, _ in hull), -2.0)
        self.assertAlmostEqual(max(x for x, _ in hull), 11.0)

    def test_densify_keeps_vertices_and_fills_edges(self) -> None:
        square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        dense = densify(square, step=0.5)
        self.assertEqual(len(dense), 16)
        self.assertIn((1.0, 0.0), dense)

    def test_span(self) -> None:
        span = Span(1.0, 4.0)
        self.assertAlmostEqual(span.length, 3.0)
        self.assertAlmostEqual(span.centre, 2.5)
        self.assertTrue(span.overlaps(Span(3.0, 5.0)))
        self.assertFalse(span.overlaps(Span(4.0, 5.0)))
        self.assertEqual(span.shifted(2.0), Span(3.0, 6.0))
