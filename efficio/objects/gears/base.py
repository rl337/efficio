"""Abstract rotary drivers: anything that turns and passes motion on.

Concrete gears (``SpurGear``, ``CrownGear``, the simple gears) are
``AbstractCogwheel`` subclasses; sprockets and pulleys are placeholders.
"""

from efficio.measures import Measure
from efficio.objects.base import EfficioObject


class AbstractRotaryDriver(EfficioObject):
    _maximum_radius: Measure
    _thickness: Measure

    """Abstract base class for any rotating object that transfers motion."""

    def __init__(self, maximum_radius: Measure, thickness: Measure):
        super().__init__()
        self._maximum_radius = maximum_radius
        self._thickness = thickness

    def get_maximum_radius(self) -> Measure:
        return self._maximum_radius

    def get_thickness(self) -> Measure:
        return self._thickness


class AbstractCogwheel(AbstractRotaryDriver):
    """Represents any rotating driver that engages via teeth."""

    _tooth_count: int

    def __init__(self, maximum_radius: Measure, tooth_count: int, thickness: Measure):
        super().__init__(maximum_radius, thickness)
        self._tooth_count = tooth_count

    def get_tooth_count(self) -> int:
        return self._tooth_count


class AbstractSprocket(AbstractCogwheel):
    """A sprocket that engages with a chain or track instead of another gear."""

    pass  # Placeholder for future functionality


class AbstractPulley(AbstractRotaryDriver):
    """A pulley that transfers motion via friction (e.g., belt drives)."""

    pass  # Placeholder for future functionality
