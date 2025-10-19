import unittest

import efficio


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

        from efficio.objects.m3 import (
            M3_HEAD_HEIGHT_MILLIMETERS,
            M3_HEAD_RADIUS_MILLIMETERS,
        )

        bolt_shape = bolt.shape()
        assert bolt_shape is not None
        self.assertIsNotNone(bolt_shape)

        bolt_bounds = bolt_shape.bounds()
        assert bolt_bounds is not None

        self.assertIsNotNone(bolt_bounds)

        # min/max x
        self.assertAlmostEqual(bolt_bounds[0], -M3_HEAD_RADIUS_MILLIMETERS.value())
        self.assertAlmostEqual(bolt_bounds[3], M3_HEAD_RADIUS_MILLIMETERS.value())

        # min/max y
        self.assertAlmostEqual(bolt_bounds[1], -M3_HEAD_RADIUS_MILLIMETERS.value())
        self.assertAlmostEqual(bolt_bounds[4], M3_HEAD_RADIUS_MILLIMETERS.value())

        # min/max z
        self.assertAlmostEqual(bolt_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(bolt_bounds[5], M3_HEAD_HEIGHT_MILLIMETERS.value() + 13)

    def test_m3_bolt_assembly_no_clearance(self) -> None:
        bolt = efficio.M3BoltAssembly(efficio.Millimeter(13.0), False)
        self.assertIsNotNone(bolt)

        from efficio.objects.m3 import (
            M3_HEAD_HEIGHT_MILLIMETERS,
            M3_NUT_HEIGHT_MILLIMETERS,
            M3_NUT_WAC_MILLIMETERS,
            M3_NUT_WAF_MILLIMETERS,
        )

        bolt_shape = bolt.shape()
        assert bolt_shape is not None
        self.assertIsNotNone(bolt_shape)

        bolt_bounds = bolt_shape.bounds()
        assert bolt_bounds is not None

        self.assertIsNotNone(bolt_bounds)

        # min/max x
        self.assertAlmostEqual(bolt_bounds[0], -M3_NUT_WAC_MILLIMETERS.value() / 2)
        self.assertAlmostEqual(bolt_bounds[3], M3_NUT_WAC_MILLIMETERS.value() / 2)

        # min/max y
        self.assertAlmostEqual(bolt_bounds[1], -M3_NUT_WAF_MILLIMETERS.value() / 2)
        self.assertAlmostEqual(bolt_bounds[4], M3_NUT_WAF_MILLIMETERS.value() / 2)

        # min/max z
        self.assertAlmostEqual(bolt_bounds[2], efficio.Millimeter(0.0).value())
        self.assertAlmostEqual(bolt_bounds[5], M3_HEAD_HEIGHT_MILLIMETERS.value() + 13)
