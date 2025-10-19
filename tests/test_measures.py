import unittest

from efficio.measures import *


class TestMeasures(unittest.TestCase):

    def test_static_measure(self) -> None:
        mm = Millimeter(10)
        self.assertAlmostEqual(mm.value(), 10)

        inch = Inch(10)
        self.assertAlmostEqual(inch.value(), 254)

    def test_compound_measure(self) -> None:
        component = Inch(3.0 / 8.0)  # a component 3/8ths of an inch
        assembly = CompoundMeasure(component, 80)  # the assembly is 80 of them
        self.assertAlmostEqual(assembly.value(), Inch(30.0).value())
