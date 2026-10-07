"""Printable face markings shared by Efficio gear families.

The marking geometry intentionally avoids font-outline booleans.  Each glyph is
assembled from a small set of rectangular strokes, which keeps OpenCascade
booleans predictable and gives FDM printing an explicit minimum feature width.
"""

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from efficio.objects.shapes import Orientation, Shape, new_shape


# Simple stencil segments.  The alphabet is deliberately limited to the
# characters used by standard Efficio gear identity labels.
_SEGMENTS: Dict[str, str] = {
    "e": "tmbl",
    "f": "tml",
    "i": "vd",
    "c": "tbl",
    "o": "tblr",
    "0": "tblr",
    "1": "r",
    "2": "tmqbu",
    "3": "tmqbr",
    "4": "mlrq",
    "5": "tmlqb",
    "6": "tmlqbr",
    "7": "tqr",
    "8": "tmlqbr",
    "9": "tmlqr",
    "T": "tv",
    "M": "lrxy",
    "P": "tmlq",
    "A": "tmlr",
    ".": "d",
    "-": "m",
}


@dataclass(frozen=True)
class GearMarkingStyle:
    """FDM-oriented dimensions for recessed gear identification."""

    stroke_width: float = 0.8
    depth: float = 0.55
    maker_height: float = 3.4
    specification_height: float = 2.6


@dataclass(frozen=True)
class GearArcMarking:
    text: str
    radius: float
    center_degrees: float
    span_degrees: float
    height: float


class GearFaceMarker:
    """Cuts readable, radially oriented stencil text into a flat gear face.

    Text ordering and glyph orientation are intentionally separate.  Looking at
    the marked +Z face, characters progress clockwise along the requested arc,
    while the top of every glyph points radially inward toward the gear axis.
    This prevents the mirror/orientation coupling that previously made curved
    labels easy to get subtly wrong.
    """

    def __init__(self, thickness: float, style: GearMarkingStyle = GearMarkingStyle()):
        self.thickness = float(thickness)
        self.style = style

    def _segments(
        self, character: str, height: float
    ) -> Iterable[Tuple[float, float, float, float]]:
        width = height * 0.60
        stroke = self.style.stroke_width
        for segment in _SEGMENTS.get(character, ""):
            if segment == "t":
                yield 0.0, height / 2.0, width, stroke
            elif segment == "m":
                yield 0.0, 0.0, width, stroke
            elif segment == "b":
                yield 0.0, -height / 2.0, width, stroke
            elif segment == "l":
                yield -width / 2.0, 0.0, stroke, height
            elif segment == "r":
                yield width / 2.0, 0.0, stroke, height
            elif segment == "v":
                yield 0.0, 0.0, stroke, height
            elif segment == "d":
                yield 0.0, -height * 0.62, stroke, stroke
            elif segment == "q":
                yield width / 2.0, height / 4.0, stroke, height / 2.0
            elif segment == "u":
                yield -width / 2.0, -height / 4.0, stroke, height / 2.0
            elif segment == "x":
                yield -width / 4.0, height / 4.0, stroke, height * 0.70
            elif segment == "y":
                yield width / 4.0, height / 4.0, stroke, height * 0.70

    def character_angles(self, marking: GearArcMarking) -> List[float]:
        """Angles in display order when the +Z gear face is viewed directly."""
        if len(marking.text) <= 1:
            return [marking.center_degrees]
        return [
            marking.center_degrees
            + marking.span_degrees / 2.0
            - marking.span_degrees * index / (len(marking.text) - 1)
            for index in range(len(marking.text))
        ]

    def cut_arc(self, shape: Shape, marking: GearArcMarking) -> Shape:
        """Cut one arc of text using small independent booleans per stroke."""
        for character, degrees in zip(marking.text, self.character_angles(marking)):
            if character == " ":
                continue
            radians = math.radians(degrees)
            x = marking.radius * math.cos(radians)
            y = marking.radius * math.sin(radians)

            for local_x, local_y, width, height in self._segments(
                character, marking.height
            ):
                # The local glyph is constructed with +Y as "up".  Negating
                # both local coordinates and then rotating by theta + 90 keeps
                # glyph tops aimed toward the hub without mirroring the face-view
                # character ordering.
                cutter = (
                    new_shape(Orientation.Front)
                    .box(width, height, self.style.depth)
                    .translate(
                        -local_x,
                        -local_y,
                        self.thickness - self.style.depth / 2.0,
                    )
                    .rotate(0.0, 0.0, degrees + 90.0)
                    .translate(x, y, 0.0)
                )
                shape = shape.cut(cutter)
        return shape


def standard_involute_markings(
    tooth_count: int,
    module: float,
    pressure_angle_degrees: float,
    marking_radius: float,
    style: GearMarkingStyle = GearMarkingStyle(),
) -> List[GearArcMarking]:
    """Return the standard Efficio maker and mating-data arcs."""
    return [
        GearArcMarking(
            text="efficio",
            radius=marking_radius,
            center_degrees=90.0,
            span_degrees=62.0,
            height=style.maker_height,
        ),
        GearArcMarking(
            text=f"{tooth_count}T M{module:.3f} PA{pressure_angle_degrees:g}",
            radius=marking_radius,
            center_degrees=270.0,
            span_degrees=122.0,
            height=style.specification_height,
        ),
    ]
