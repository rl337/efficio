import re
from typing import List

class Measure:

    @staticmethod
    def ratio() -> float:
        raise NotImplementedError('Measure::ratio()')

    def value(self) -> float:
        raise NotImplementedError('Measure::value()')
    
    @staticmethod
    def examples() -> List[str]:
        return ["3mm", "2in", "5 inches"]


class StaticMeasure(Measure):
    _value: float

    def __init__(self, value: float):
        self._value = value
    
    @staticmethod
    def ratio() -> float:
        raise NotImplementedError()

    def value(self) -> float:
        return self._value * self.ratio()


class CompoundMeasure(Measure):
    _measure: Measure
    _value: float

    def __init__(self, measure: Measure, value: float):
        self._measure = measure
        self._value = value

    def value(self) -> float:
        return self._measure.value() * self._value

class Millimeter(StaticMeasure):

    @staticmethod
    def ratio() -> float:
        return 1.0

class Inch(StaticMeasure):

    @staticmethod
    def ratio() -> float:
        return 25.4

def parse_measure(value: str) -> Measure:
    pattern = r'^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]*)\s*$'
    match = re.match(pattern, value)
    if not match:
        raise ValueError(f"Invalid distance value: '{value}'")
    
    float_value = float(match.group('value'))
    unit = match.group('unit').lower()

    canonical_units = {
        'mm': Millimeter,
        'millimeter': Millimeter,
        'in': Inch,
        'inch': Inch,
        'inches': Inch,
    }

    if unit and unit not in canonical_units:
        raise ValueError(f"Unknown unit: '{unit}'")

    canonical_unit = canonical_units.get(unit, Millimeter)  # Default to millimeters if no unit provided

    return canonical_unit(float_value)

