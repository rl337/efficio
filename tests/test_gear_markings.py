"""Regression checks for the recovered, shared face-marking strokes."""

import math
import unittest
from unittest.mock import patch

import cadquery as cq

from efficio.objects.gears.markings import (
    GearArcMarking,
    GearFaceMarker,
    GearMarkingStyle,
    standard_involute_markings,
)
from efficio.objects.shapes import Orientation, Shape, new_shape


def _solid(shape: Shape) -> cq.Shape:
    solid = shape.workplane().val()
    assert isinstance(solid, cq.Shape)
    return solid


class TestGearMarkings(unittest.TestCase):
    def test_counterclockwise_order_follows_inward_glyph_reading_direction(
        self,
    ) -> None:
        marker = GearFaceMarker(8)
        marking = GearArcMarking("T M", 15, 90, 60, 3)
        self.assertEqual(marker.character_angles(marking), [60, 90, 120])
        self.assertEqual(
            marker.character_angles(GearArcMarking("T", 15, 37, 60, 3)), [37]
        )
        self.assertEqual(marker.character_angles(GearArcMarking("", 15, 37, 60, 3)), [])

    def test_progression_follows_glyph_positive_x_on_top_and_bottom_arcs(self) -> None:
        marker = GearFaceMarker(8)
        for center in (90, 270):
            marking = GearArcMarking("123", 15, center, 60, 4)
            angles = marker.character_angles(marking)
            for first, second in zip(angles, angles[1:]):
                theta, following = map(math.radians, (first, second))
                dx = marking.radius * (math.cos(following) - math.cos(theta))
                dy = marking.radius * (math.sin(following) - math.sin(theta))
                # The cutter rotates local +X by theta+90. Progress toward the
                # next character must have a positive projection on that axis.
                reading_x = (
                    math.cos(theta + math.pi / 2),
                    math.sin(theta + math.pi / 2),
                )
                self.assertGreater(dx * reading_x[0] + dy * reading_x[1], 0)

    def test_digits_have_distinct_correct_actual_seven_segment_geometry(self) -> None:
        marker = GearFaceMarker(8)
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        # Independent probes at each half-stroke's center, in local glyph axes.
        probes = {
            "top": (0, 2),
            "ul": (-1.2, 1),
            "ur": (1.2, 1),
            "middle": (0, 0),
            "ll": (-1.2, -1),
            "lr": (1.2, -1),
            "bottom": (0, -2),
        }
        expected = {
            "0": {"top", "ul", "ur", "ll", "lr", "bottom"},
            "1": {"ur", "lr"},
            "2": {"top", "ur", "middle", "ll", "bottom"},
            "3": {"top", "ur", "middle", "lr", "bottom"},
            "4": {"ul", "ur", "middle", "lr"},
            "5": {"top", "ul", "middle", "lr", "bottom"},
            "6": {"top", "ul", "middle", "ll", "lr", "bottom"},
            "7": {"top", "ur", "lr"},
            "8": set(probes),
            "9": {"top", "ul", "ur", "middle", "lr", "bottom"},
        }
        geometries = set()
        for digit, occupied in expected.items():
            cutters: list[Shape] = []

            def capture(shape: Shape, cutter: Shape) -> Shape:
                cutters.append(cutter)
                return shape

            # theta=270 rotates local axes by 360 degrees, keeping +X/+Y.
            with patch.object(type(blank), "cut", capture):
                marker.cut_arc(blank, GearArcMarking(digit, 15, 270, 0, 4))
            bounds = [_solid(cutter).BoundingBox() for cutter in cutters]
            actual = {
                name
                for name, (x, y) in probes.items()
                if any(b.xmin < x < b.xmax and b.ymin < y - 15 < b.ymax for b in bounds)
            }
            self.assertEqual(actual, occupied, digit)
            geometries.add(frozenset(marker._segments(digit, 4)))
        self.assertEqual(len(geometries), 10)

    def test_actual_asymmetric_glyph_cutter_points_inward_without_mirroring(
        self,
    ) -> None:
        marker = GearFaceMarker(8)
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        cutters: list[Shape] = []

        def capture(shape: Shape, cutter: Shape) -> Shape:
            cutters.append(cutter)
            return shape

        # F has a top crossbar and a left upright, independently exposing both
        # upside-down and mirrored glyphs. At theta=90 local axes are -X/-Y.
        with patch.object(type(blank), "cut", capture):
            marker.cut_arc(blank, GearArcMarking("f", 15, 90, 0, 4))
        centers = [_solid(c).Center() for c in cutters]
        self.assertEqual(len(centers), 3)
        self.assertAlmostEqual(centers[0].x, 0)
        self.assertAlmostEqual(centers[0].y, 13)  # top toward hub
        self.assertAlmostEqual(centers[1].y, 15)  # middle
        self.assertAlmostEqual(centers[2].x, 1.2)  # left, not mirrored
        self.assertAlmostEqual(centers[2].y, 15)
        self.assertAlmostEqual(centers[0].z, 8 - marker.style.depth / 2)

    def test_lowercase_i_dot_is_inward_and_decimal_dot_is_outward(self) -> None:
        marker = GearFaceMarker(8)
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        for character, expected_radii in (("i", [15.36, 12.52]), (".", [17.48])):
            cutters: list[Shape] = []

            def capture(shape: Shape, cutter: Shape) -> Shape:
                cutters.append(cutter)
                return shape

            with patch.object(type(blank), "cut", capture):
                marker.cut_arc(blank, GearArcMarking(character, 15, 37, 0, 4))
            self.assertEqual(len(cutters), len(expected_radii))
            for cutter, expected in zip(cutters, expected_radii):
                center = _solid(cutter).Center()
                self.assertAlmostEqual(math.hypot(center.x, center.y), expected)

    def test_lowercase_i_has_printable_gap_between_actual_cutters(self) -> None:
        for height in (0.5, 2.6, 3.4, 5.0):
            marker = GearFaceMarker(8)
            blank = new_shape(Orientation.Front).circle(25).extrude(8)
            cutters: list[Shape] = []

            def capture(shape: Shape, cutter: Shape) -> Shape:
                cutters.append(cutter)
                return shape

            marking = GearArcMarking("i", 15, 37, 0, height)
            with patch.object(type(blank), "cut", capture):
                marker.cut_arc(blank, marking)
            stem, dot = map(_solid, cutters)
            self.assertAlmostEqual(stem.distance(dot), marker.style.stroke_width)
            self.assertGreaterEqual(stem.Volume(), dot.Volume() - 1e-10)
            lower, upper = marker.radial_bounds(marking)
            for cutter in (stem, dot):
                for vertex in cutter.Vertices():
                    radius = math.hypot(vertex.X, vertex.Y)
                    self.assertGreaterEqual(radius + 1e-10, lower)
                    self.assertLessEqual(radius, upper + 1e-10)

    def test_radial_bounds_enclose_actual_rotated_strokes(self) -> None:
        marker = GearFaceMarker(8)
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        for radius in (0.2, 15):
            for angle in (0, 37, 90, 217):
                marking = GearArcMarking("f.i M", radius, angle, 93, 4)
                lower, upper = marker.radial_bounds(marking)
                cutters: list[Shape] = []

                def capture(shape: Shape, cutter: Shape) -> Shape:
                    cutters.append(cutter)
                    return shape

                with patch.object(type(blank), "cut", capture):
                    marker.cut_arc(blank, marking)
                for cutter in cutters:
                    for vertex in _solid(cutter).Vertices():
                        distance = math.hypot(vertex.X, vertex.Y)
                        self.assertGreaterEqual(distance + 1e-10, lower)
                        self.assertLessEqual(distance, upper + 1e-10)
                    center = _solid(cutter).Center()
                    self.assertGreaterEqual(
                        math.hypot(center.x, center.y) + 1e-10, lower
                    )
                self.assertGreater(upper, radius + marking.height / 2)
        self.assertEqual(
            marker.radial_bounds(GearArcMarking(" ", 15, 0, 0, 4)), (15, 15)
        )

    def test_real_cut_reduces_volume_and_preserves_single_valid_solid(self) -> None:
        marker = GearFaceMarker(8, GearMarkingStyle(stroke_width=0.7, depth=0.6))
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        before = _solid(blank).Volume()
        marked = marker.cut_arc(blank, GearArcMarking("efficio", 18, 90, 62, 3.4))
        solid = _solid(marked)
        self.assertTrue(solid.isValid())
        self.assertEqual(len(solid.Solids()), 1)
        self.assertLess(solid.Volume(), before)
        self.assertGreater(solid.Volume(), before - 100)
        self.assertAlmostEqual(solid.BoundingBox().zmin, 0)
        self.assertAlmostEqual(solid.BoundingBox().zmax, 8)

    def test_spaces_do_not_cut(self) -> None:
        blank = new_shape(Orientation.Front).circle(25).extrude(8)
        with patch.object(type(blank), "cut", side_effect=AssertionError("space cut")):
            self.assertIs(
                GearFaceMarker(8).cut_arc(blank, GearArcMarking("  ", 15, 0, 30, 3)),
                blank,
            )

    def test_invalid_values_fail_before_geometry(self) -> None:
        for field in ("stroke_width", "depth", "maker_height", "specification_height"):
            for invalid_number in (0, -1, math.inf, math.nan):
                with (
                    self.subTest(field=field, value=invalid_number),
                    self.assertRaises(ValueError),
                ):
                    GearMarkingStyle(**{field: invalid_number})
        for field, value in (
            ("radius", 0),
            ("radius", math.inf),
            ("height", -1),
            ("height", math.nan),
            ("center_degrees", math.inf),
            ("span_degrees", -1),
            ("span_degrees", 361),
            ("span_degrees", math.nan),
            ("text", "unsupported!"),
        ):
            args = dict(
                text="T", radius=15, center_degrees=0, span_degrees=30, height=3
            )
            args[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                GearArcMarking(**args)  # type: ignore[arg-type]
        for thickness in (0, -1, math.inf, math.nan, 0.55):
            with self.assertRaises(ValueError):
                GearFaceMarker(thickness)

    def test_standard_labels(self) -> None:
        marks = standard_involute_markings(20, 60 / 22, 20, 20)
        self.assertEqual([m.text for m in marks], ["efficio", "20T M2.727 PA20"])
        self.assertEqual([m.center_degrees for m in marks], [90, 270])
        for count, module, pressure in (
            (2, 1, 20),
            (True, 1, 20),
            (20, 0, 20),
            (20, 1, 90),
            (20, 1, math.nan),
        ):
            with self.assertRaises(ValueError):
                standard_involute_markings(count, module, pressure, 20)
