import unittest

from efficio import renderer
from efficio.measures import Millimeter
from efficio.objects.gears import TrapezoidalGear
from efficio.objects.m3 import M3Bolt
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


if __name__ == "__main__":
    unittest.main()
