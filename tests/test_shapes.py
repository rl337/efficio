import unittest

import efficio
from efficio.objects.fasteners import MetricThread


class TestObjects(unittest.TestCase):

    def test_empty_shape(self) -> None:
        empty = efficio.new_shape()
        self.assertIsNone(empty.bounds())

    def test_circle(self) -> None:
        obj = efficio.new_shape()
        obj.circle(10.0)
        circle_bounds = obj.bounds()

        self.assertIsNotNone(circle_bounds)
        assert circle_bounds is not None

        # min/max x
        self.assertAlmostEqual(circle_bounds[0], efficio.Millimeter(-10.0).value())
        self.assertAlmostEqual(circle_bounds[3], efficio.Millimeter(10.0).value())

        # min/max y
        self.assertAlmostEqual(circle_bounds[1], efficio.Millimeter(-10.0).value())
        self.assertAlmostEqual(circle_bounds[4], efficio.Millimeter(10.0).value())

        # min/max z
        self.assertAlmostEqual(circle_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(circle_bounds[5], efficio.Millimeter(0.0).value())

    def test_cylinder(self) -> None:
        obj = efficio.new_shape()
        obj.circle(10.0)
        obj.extrude(10)

        circle_bounds = obj.bounds()
        self.assertIsNotNone(circle_bounds)
        assert circle_bounds is not None

        # min/max x
        self.assertAlmostEqual(circle_bounds[0], efficio.Millimeter(-10.0).value())
        self.assertAlmostEqual(circle_bounds[3], efficio.Millimeter(10.0).value())

        # min/max y
        self.assertAlmostEqual(circle_bounds[1], efficio.Millimeter(-10.0).value())
        self.assertAlmostEqual(circle_bounds[4], efficio.Millimeter(10.0).value())

        # min/max z
        self.assertAlmostEqual(circle_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(circle_bounds[5], efficio.Millimeter(10.0).value())

    def test_m3_bolt_no_clearance(self) -> None:
        bolt = efficio.M3Bolt(efficio.Millimeter(13.0), False)
        self.assertIsNotNone(bolt)

        m3 = MetricThread.M3.spec

        bolt_shape = bolt.shape()
        assert bolt_shape is not None
        self.assertIsNotNone(bolt_shape)

        bolt_bounds = bolt_shape.bounds()
        assert bolt_bounds is not None

        self.assertIsNotNone(bolt_bounds)

        # min/max x
        self.assertAlmostEqual(bolt_bounds[0], -m3.head_radius)
        self.assertAlmostEqual(bolt_bounds[3], m3.head_radius)

        # min/max y
        self.assertAlmostEqual(bolt_bounds[1], -m3.head_radius)
        self.assertAlmostEqual(bolt_bounds[4], m3.head_radius)

        # min/max z
        self.assertAlmostEqual(bolt_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(bolt_bounds[5], m3.head_height + 13)

    def test_m3_bolt_assembly_no_clearance(self) -> None:
        bolt = efficio.M3BoltAssembly(efficio.Millimeter(13.0), False)
        self.assertIsNotNone(bolt)

        m3 = MetricThread.M3.spec

        bolt_shape = bolt.shape()
        assert bolt_shape is not None
        self.assertIsNotNone(bolt_shape)

        bolt_bounds = bolt_shape.bounds()
        assert bolt_bounds is not None

        self.assertIsNotNone(bolt_bounds)

        # min/max x
        self.assertAlmostEqual(bolt_bounds[0], -m3.nut_across_corners / 2)
        self.assertAlmostEqual(bolt_bounds[3], m3.nut_across_corners / 2)

        # min/max y
        self.assertAlmostEqual(bolt_bounds[1], -m3.nut_across_flats / 2)
        self.assertAlmostEqual(bolt_bounds[4], m3.nut_across_flats / 2)

        # min/max z
        self.assertAlmostEqual(bolt_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(bolt_bounds[5], m3.head_height + 13)
