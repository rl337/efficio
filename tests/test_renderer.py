import unittest

import cadquery as cq

from efficio import preview, renderer
from efficio.__main__ import get_constructor_defaults, parse_color
from efficio.measures import Millimeter
from efficio.objects.fasteners import M3Bolt
from efficio.objects.gears import SpurGear, TrapezoidalGear
from efficio.objects.primitives import Box, Cylinder, Sphere


class TestRenderer(unittest.TestCase):
    def test_preview_does_not_mutate_geometry(self) -> None:
        shape = Box(Millimeter(10), Millimeter(20), Millimeter(5)).shape()
        self.assertIsNotNone(shape)
        assert shape is not None
        before_count = len(shape.workplane().vals())
        before_bounds = shape.bounds()

        first = renderer.create_composite_image(shape.workplane())
        second = renderer.create_composite_image(shape.workplane())

        self.assertEqual(first.size, second.size)
        self.assertEqual(len(shape.workplane().vals()), before_count)
        self.assertEqual(shape.bounds(), before_bounds)

    def test_known_good_geometry_renders(self) -> None:
        objects = [
            Box(Millimeter(10), Millimeter(20), Millimeter(5)),
            Cylinder(Millimeter(20), Millimeter(5)),
            Sphere(Millimeter(10)),
            M3Bolt(Millimeter(20), has_clearance=False),
            TrapezoidalGear(Millimeter(30), 16, Millimeter(8)),
        ]
        for obj in objects:
            with self.subTest(object=type(obj).__name__):
                shape = obj.shape()
                self.assertIsNotNone(shape)
                assert shape is not None
                image = renderer.create_composite_image(shape.workplane())
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)

    def test_grid_spacing_tracks_geometry_scale(self) -> None:
        self.assertEqual(renderer._nice_grid_spacing(5), 1)
        self.assertEqual(renderer._nice_grid_spacing(50), 10)
        self.assertEqual(renderer._nice_grid_spacing(500), 100)


class TestColorPreview(unittest.TestCase):
    def test_plain_object_uses_its_resolved_colour(self) -> None:
        box = Box(Millimeter(10), Millimeter(20), Millimeter(5))
        parts, legend = renderer.object_preview_parts(box, (1, 2, 3))
        self.assertEqual(parts[0][2], (1, 2, 3))
        self.assertEqual(legend, [("Box", (1, 2, 3))])
        box.with_preview_color((200, 10, 10))
        parts, _ = renderer.object_preview_parts(box, (1, 2, 3))
        self.assertEqual(parts[0][2], (200, 10, 10))

    def test_colour_composite_draws_the_colour(self) -> None:
        box = Box(Millimeter(10), Millimeter(20), Millimeter(5)).with_preview_color(
            (220, 30, 30)
        )
        image = renderer.create_object_preview(box)
        legend_height = renderer.LEGEND_ROW_HEIGHT
        self.assertEqual(
            image.size,
            (
                2 * renderer.DEFAULT_PREVIEW_STYLE.panel_width,
                2 * renderer.DEFAULT_PREVIEW_STYLE.panel_height + legend_height,
            ),
        )
        colors = image.getcolors(maxcolors=image.width * image.height) or []
        reds = 0
        for count, color in colors:
            assert isinstance(color, tuple)
            r, g, b = color[:3]
            if r > 100 and g < 60 and b < 60:
                reds += count
        self.assertGreater(reds, 1000)

    def test_crossing_triangles_resolve_depth_per_pixel(self) -> None:
        red = ((-1.0, -1.0, -1.0), (1.0, -1.0, 1.0), (0.0, 1.0, 0.0))
        blue = ((-1.0, -1.0, 1.0), (1.0, -1.0, -1.0), (0.0, 1.0, 0.0))
        triangles = [(red, (240, 0, 0)), (blue, (0, 0, 240))]
        style = renderer.PreviewStyle(panel_width=120, panel_height=120, margin=10)
        first = renderer.create_color_view(
            triangles, preview.TOP, style=style, show_grid=False
        )
        second = renderer.create_color_view(
            list(reversed(triangles)), preview.TOP, style=style, show_grid=False
        )
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(
            first.getpixel((35, 80)),
            preview.shade((0, 0, 240), preview.triangle_normal(blue), preview.TOP),
        )
        self.assertEqual(
            first.getpixel((85, 80)),
            preview.shade((240, 0, 0), preview.triangle_normal(red), preview.TOP),
        )

    def test_flat_tessellated_surface_has_no_cracks_in_either_winding(self) -> None:
        a, b, c, d = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)
        style = renderer.PreviewStyle(panel_width=120, panel_height=120, margin=10)
        for triangles in (((a, b, c), (a, c, d)), ((c, b, a), (d, c, a))):
            with self.subTest(triangles=triangles):
                image = renderer.create_color_view(
                    [(triangle, (200, 100, 20)) for triangle in triangles],
                    preview.TOP,
                    style=style,
                    show_grid=False,
                )
                expected = preview.shade((200, 100, 20), (0, 0, 1), preview.TOP)
                self.assertEqual(
                    image.crop((10, 10, 110, 110)).getcolors(), [(10000, expected)]
                )
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_real_cad_nearer_box_hides_back_box(self) -> None:
        back = cq.Workplane("XY").box(10, 10, 1).val()
        front = cq.Workplane("XY").box(10, 10, 1).translate((0, 0, 3)).val()
        assert isinstance(back, cq.Shape) and isinstance(front, cq.Shape)
        triangles = renderer.tessellate_parts(
            [("front", front, (0, 200, 0)), ("back", back, (200, 0, 0))]
        )
        style = renderer.PreviewStyle(panel_width=120, panel_height=120, margin=10)
        image = renderer.create_color_view(triangles, preview.TOP, style=style)
        expected = preview.shade((0, 200, 0), (0, 0, 1), preview.TOP)
        self.assertEqual(
            image.crop((10, 10, 110, 110)).getcolors(), [(10000, expected)]
        )

    def test_grid_remains_background_and_degenerate_triangles_are_skipped(self) -> None:
        triangle = ((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 1.0, 0.0))
        edge = ((-1.0, 0.0, 10.0), (1.0, 0.0, 10.0), (0.0, 0.0, 10.0))
        style = renderer.PreviewStyle(panel_width=120, panel_height=120, margin=10)
        image = renderer.create_color_view(
            [(triangle, (200, 0, 0)), (edge, (0, 0, 200))],
            preview.TOP,
            style=style,
        )
        self.assertEqual(image.getpixel((15, 60)), (205, 205, 205))
        self.assertEqual(
            image.getpixel((60, 60)), preview.shade((200, 0, 0), (0, 0, 1), preview.TOP)
        )

    def test_empty_preview_rejected(self) -> None:
        with self.assertRaises(ValueError):
            renderer.create_color_composite_image([])


class TestCommandLineHelpers(unittest.TestCase):
    def test_parse_color(self) -> None:
        self.assertEqual(parse_color("#336699"), (0x33, 0x66, 0x99))
        self.assertEqual(parse_color("10,20,30"), (10, 20, 30))
        for bad in ("#12345", "300,0,0", "1,2"):
            with self.assertRaises(ValueError):
                parse_color(bad)

    def test_constructor_defaults(self) -> None:
        defaults = get_constructor_defaults(SpurGear)
        self.assertIn("pressure_angle", defaults)
        self.assertNotIn("teeth", defaults)


if __name__ == "__main__":
    unittest.main()
