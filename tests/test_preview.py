import unittest

from efficio.preview import (
    FRONT,
    ISOMETRIC,
    SIDE,
    STANDARD_VIEWS,
    TOP,
    View,
    Viewport,
    normalize,
    paint_order,
    shade,
)


class TestViews(unittest.TestCase):
    def test_bases_are_orthonormal(self) -> None:
        for view in STANDARD_VIEWS:
            with self.subTest(view=view.title):
                r, u, f = view.right, view.up, view.forward
                for a, b in ((r, u), (u, f), (r, f)):
                    self.assertAlmostEqual(sum(x * y for x, y in zip(a, b)), 0.0)
                for v in (r, u, f):
                    self.assertAlmostEqual(sum(x * x for x in v), 1.0)

    def test_up_is_up(self) -> None:
        for view in (FRONT, SIDE, ISOMETRIC):
            self.assertGreater(view.project((0, 0, 1))[1], 0.0, view.title)
        # Top view: forward to the right, right-hand (+y) side up the page.
        self.assertGreater(TOP.project((1, 0, 0))[0], 0.0)
        self.assertGreater(TOP.project((0, 1, 0))[1], 0.0)

    def test_view_handedness(self) -> None:
        # From ahead, the vehicle's left (-y) appears on the viewer's left.
        self.assertLess(FRONT.project((0, -1, 0))[0], 0.0)
        # Side view from the left: forward (+x) is to the right.
        self.assertGreater(SIDE.project((1, 0, 0))[0], 0.0)
        # Points nearer the camera have larger depth.
        self.assertGreater(FRONT.project((5, 0, 0))[2], FRONT.project((0, 0, 0))[2])

    def test_normalize_rejects_zero(self) -> None:
        with self.assertRaises(ValueError):
            normalize((0.0, 0.0, 0.0))


class TestShading(unittest.TestCase):
    def test_shade_is_two_sided_and_bounded(self) -> None:
        color = (200, 100, 50)
        lit = shade(color, (1, 0, 0), FRONT)
        self.assertEqual(lit, shade(color, (-1, 0, 0), FRONT))
        self.assertLessEqual(max(lit), 200)
        edge_on = shade(color, FRONT.right, FRONT)
        self.assertLess(sum(edge_on), sum(lit))
        self.assertEqual(shade(color, (0, 0, 0), FRONT), color)


class TestPainter(unittest.TestCase):
    def test_far_triangles_paint_first(self) -> None:
        near = (((1, 0, 0), (1, 1, 0), (1, 0, 1)), (255, 0, 0))
        far = (((-1, 0, 0), (-1, 1, 0), (-1, 0, 1)), (0, 0, 255))
        polygons, _ = paint_order([near, far], FRONT, 200, 100, 10)
        self.assertEqual(len(polygons), 2)
        self.assertLess(polygons[0][2], polygons[1][2])
        self.assertGreater(polygons[1][1][0], polygons[1][1][2])  # red last

    def test_viewport_fits_and_preserves_aspect(self) -> None:
        viewport = Viewport.fit([(0, 0), (10, 5)], 220, 120, 10)
        self.assertAlmostEqual(viewport.scale, 20.0)
        x0, y0 = viewport.to_pixels(0, 0)
        x1, y1 = viewport.to_pixels(10, 5)
        self.assertAlmostEqual(x0, 10.0)
        self.assertAlmostEqual(x1, 210.0)
        self.assertGreater(y0, y1)  # +y goes up the image
        with self.assertRaises(ValueError):
            Viewport.fit([], 10, 10, 1)

    def test_custom_view(self) -> None:
        view = View("custom", (0, 0, 2), (1, 0, 0))
        self.assertAlmostEqual(view.forward[2], 1.0)
