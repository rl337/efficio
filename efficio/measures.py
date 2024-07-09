
class Measure:

    @staticmethod
    def ratio() -> float:
        raise NotImplementedError('Measure::ratio()')

    def value(self) -> float:
        raise NotImplementedError('Measure::value()')

        result = 1.0
        if self._measure is not None:
            result *= self._measure.value()
        return self._value * self.ratio()


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
