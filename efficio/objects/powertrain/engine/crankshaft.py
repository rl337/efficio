"""Built-up crankshaft parts.

Model-engine practice: flat webs (CNC plate or printed) are pressed onto
ground-rod journals and crankpins (:class:`~efficio.objects.powertrain.shafts.Shaft`),
so connecting rods can be one piece and every rotating part stays 2.5D.
"""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fits import PRESS_CLEARANCE_MM
from efficio.objects.planar import hull_of_circles
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.profiles import cylinder, prism, wrap
from efficio.objects.shapes import Shape


class CrankWeb(EfficioObject):
    """Crank throw plate: journal on the origin, crankpin on local +X."""

    def __init__(
        self,
        throw: Measure,
        journal_diameter: Measure,
        crankpin_diameter: Measure,
        thickness: Measure,
        journal_boss_radius: Measure,
        pin_boss_radius: Measure,
    ):
        self.throw = throw
        self.journal_diameter = journal_diameter
        self.crankpin_diameter = crankpin_diameter
        self.thickness = thickness
        self.journal_boss_radius = journal_boss_radius
        self.pin_boss_radius = pin_boss_radius

    @classmethod
    def from_engine(cls, engine: EngineGeometry) -> "CrankWeb":
        return cls(
            Millimeter(engine.crank_throw),
            Millimeter(engine.crank_journal_diameter),
            Millimeter(engine.crankpin_diameter),
            Millimeter(engine.web_thickness),
            Millimeter(engine.web_journal_radius),
            Millimeter(engine.web_pin_radius),
        )

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        throw = self.throw.value()
        profile = hull_of_circles(
            [
                ((0.0, 0.0), self.journal_boss_radius.value()),
                ((throw, 0.0), self.pin_boss_radius.value()),
            ]
        )
        web = prism(profile, 0.0, t)
        journal = self.journal_diameter.value() / 2 + PRESS_CLEARANCE_MM
        pin = self.crankpin_diameter.value() / 2 + PRESS_CLEARANCE_MM
        web = web.cut(cylinder(journal, -1, t + 1))
        web = web.cut(cylinder(pin, -1, t + 1, throw))
        return wrap(web)
