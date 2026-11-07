"""Reusable axis-Z hose barb: integral boss or separately fabricated solid.

No thread, gasket or proprietary hose rating is implied. Mounting/sealing a
separate instance needs a separately designed interface; integral use avoids it.
"""

from typing import Optional

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.connectors.geometry import HoseBarbDimensions
from efficio.objects.profiles import wrap
from efficio.objects.shapes import Shape


class HoseBarb(EfficioObject):
    def __init__(self, dimensions: HoseBarbDimensions):
        self.dimensions = dimensions

    def envelope(self) -> cq.Shape:
        d = self.dimensions
        solid: cq.Shape = cq.Solid.makeCylinder(d.stem_radius, d.length)
        for start in d.barb_starts:
            solid = solid.fuse(
                cq.Solid.makeCone(
                    d.barb_radius, d.stem_radius, d.barb_length, cq.Vector(0, 0, start)
                )
            )
        return solid.clean()

    def bore(self) -> cq.Shape:
        d = self.dimensions
        return cq.Solid.makeCylinder(
            d.bore_radius, d.length + 0.02, cq.Vector(0, 0, -0.01)
        )

    def access_envelope(self) -> cq.Shape:
        """Conservative hose/clamp outside envelope; excludes the terminal itself."""
        d = self.dimensions
        return cq.Solid.makeCylinder(
            d.access_radius, d.length - d.hose_start, cq.Vector(0, 0, d.hose_start)
        )

    def shape(self) -> Optional[Shape]:
        return wrap(cq.Workplane("XY").newObject([self.envelope().cut(self.bore())]))
