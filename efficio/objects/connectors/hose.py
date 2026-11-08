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

    def barbed_stem(self) -> cq.Shape:
        d = self.dimensions
        solid: cq.Shape = cq.Solid.makeCylinder(d.stem_radius, d.length)
        for start in d.barb_starts:
            solid = solid.fuse(
                cq.Solid.makeCone(
                    d.barb_radius, d.stem_radius, d.barb_length, cq.Vector(0, 0, start)
                )
            )
        return solid.clean()

    def root_envelope(self) -> Optional[cq.Shape]:
        """Analytic tapered boss with a rounded cone-to-stem transition."""
        d = self.dimensions
        if d.root_radius == 0:
            return None
        blend = min((d.root_radius - d.stem_radius) / 2, d.root_length / 8)
        taper = d.root_length - blend
        solid = (
            cq.Solid.makeCone(d.root_radius, d.stem_radius, taper)
            .fuse(cq.Solid.makeCylinder(d.stem_radius, d.root_length))
            .clean()
        )
        neck = [edge for edge in solid.Edges() if abs(edge.Center().z - taper) < 1e-7]
        value = (
            cq.Workplane("XY").newObject([solid]).newObject(neck).fillet(blend).val()
        )
        assert isinstance(value, cq.Shape)
        return value

    def envelope(self) -> cq.Shape:
        stem = self.barbed_stem()
        root = self.root_envelope()
        return stem if root is None else stem.fuse(root).clean()

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
