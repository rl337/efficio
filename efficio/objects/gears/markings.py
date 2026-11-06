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
    "i": "kj",
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


def _positive_finite(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class GearMarkingStyle:
    """FDM-oriented dimensions for recessed gear identification."""

    stroke_width: float = 0.8
    depth: float = 0.55
    maker_height: float = 3.4
    specification_height: float = 2.6

    def __post_init__(self) -> None:
        for name in ("stroke_width", "depth", "maker_height", "specification_height"):
            _positive_finite(name, getattr(self, name))


@dataclass(frozen=True)
class GearArcMarking:
    text: str
    radius: float
    center_degrees: float
    span_degrees: float
    height: float

    def __post_init__(self) -> None:
        _positive_finite("radius", self.radius)
        _positive_finite("height", self.height)
        if not math.isfinite(self.center_degrees):
            raise ValueError("center_degrees must be finite")
        if not math.isfinite(self.span_degrees) or not 0 <= self.span_degrees <= 360:
            raise ValueError("span_degrees must be between 0 and 360")
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        unsupported = set(self.text) - set(_SEGMENTS) - {" "}
        if unsupported:
            raise ValueError(f"Unsupported marking characters: {sorted(unsupported)}")


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
        _positive_finite("thickness", self.thickness)
        if style.depth >= self.thickness:
            raise ValueError("marking depth must be less than thickness")

    def _segments(
        self, character: str, height: float
    ) -> Iterable[Tuple[float, float, float, float]]:
        width = height * 0.60
        stroke = self.style.stroke_width
        # Keep i's lower stem and dot separated by a full printable stroke.
        # For very small requested glyphs preserve stroke size and move the dot
        # upward; radial_bounds includes this extension in clearance checks.
        i_stem_height = max(stroke, height * 1.12 - 1.5 * stroke)
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
            elif segment == "k":
                yield 0.0, -height / 2 + i_stem_height / 2, stroke, i_stem_height
            elif segment == "j":
                yield 0.0, -height / 2 + i_stem_height + 1.5 * stroke, stroke, stroke
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
        if not marking.text:
            return []
        if len(marking.text) == 1:
            return [marking.center_degrees]
        return [
            marking.center_degrees
            + marking.span_degrees / 2.0
            - marking.span_degrees * index / (len(marking.text) - 1)
            for index in range(len(marking.text))
        ]

    def radial_bounds(self, marking: GearArcMarking) -> Tuple[float, float]:
        """Enclose every full stroke rectangle, not only glyph centerlines.

        Rotation about the gear axis preserves radius. In a glyph's tangent /
        radial coordinates a point has radius hypot(local_x, radius-local_y).
        The nearest point is the origin clamped to that rectangle and the
        furthest point is a corner. Spaces have no strokes; an empty label
        returns its nominal radius twice.
        """
        minima: List[float] = []
        maxima: List[float] = []
        for character in marking.text:
            for x, y, width, height in self._segments(character, marking.height):
                radial = marking.radius - y
                minima.append(
                    math.hypot(
                        max(abs(x) - width / 2, 0), max(abs(radial) - height / 2, 0)
                    )
                )
                maxima.append(math.hypot(abs(x) + width / 2, abs(radial) + height / 2))
        if not minima:
            return marking.radius, marking.radius
        return min(minima), max(maxima)

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
                # +Y rotated by theta + 90 points radially inward. Keep
                # coordinates unchanged: negation would turn tops outward.
                cutter = (
                    new_shape(Orientation.Front)
                    .box(width, height, self.style.depth)
                    .translate(
                        local_x,
                        local_y,
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
    if (
        isinstance(tooth_count, bool)
        or not isinstance(tooth_count, int)
        or tooth_count < 3
    ):
        raise ValueError("tooth_count must be an integer of at least 3")
    _positive_finite("module", module)
    if not math.isfinite(pressure_angle_degrees) or not 0 < pressure_angle_degrees < 90:
        raise ValueError("pressure_angle_degrees must be between 0 and 90")
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
