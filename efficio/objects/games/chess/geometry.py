"""Pure dimensions for the stylized stacking-chess set (no CadQuery).

All lengths are millimetres. Each piece stands on +Z with its base at z = 0;
heights inside a piece's head are measured from the top of its shoulder.
The defaults reproduce the prototype set sized for 1.75 in board squares
(32 mm base inside a 38 mm clear-resin cylinder).  The set is compact: each
piece is roughly half the height of the first prototype, with a single rounded
base disc and a short stem under the shoulder.
"""

import math
from dataclasses import dataclass, fields
from typing import List, Tuple

Point = Tuple[float, float]
Cubic = Tuple[Point, Point, Point, Point]


def quadratic_bezier(p0: Point, p1: Point, p2: Point, samples: int) -> List[Point]:
    """``samples + 1`` points along a quadratic Bezier, endpoints included."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    points = []
    for i in range(samples + 1):
        t = i / samples
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        points.append(
            (a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1])
        )
    return points


def cubic_bezier(curve: Cubic, samples: int) -> List[Point]:
    """``samples + 1`` points along a cubic Bezier, endpoints included."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    p0, p1, p2, p3 = curve
    points = []
    for i in range(samples + 1):
        t = i / samples
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t**3
        points.append(
            (
                a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
            )
        )
    return points


def _positive(obj: object, exempt: Tuple[str, ...] = ()) -> List[str]:
    problems = []
    for f in fields(obj):  # type: ignore[arg-type]
        value = getattr(obj, f.name)
        if f.name in exempt or isinstance(value, (bool, tuple)):
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(f"{f.name} must be a finite number")
        elif value <= 0:
            problems.append(f"{f.name} must be positive")
    return problems


class _Validated:
    def problems(self) -> List[str]:
        raise NotImplementedError

    def __post_init__(self) -> None:
        problems = self.problems()
        if problems:
            raise ValueError("; ".join(problems))


@dataclass(frozen=True)
class ChessBodyDimensions(_Validated):
    """Shared base, stem and shoulder of every piece.

    The base is one cylinder with both circular edges rounded by ``base_round``.
    """

    base_radius: float = 16.0
    base_height: float = 7.0
    base_round: float = 2.5  # fillet on the top and bottom edge of the base
    edge_round: float = 1.2  # both shoulder edges
    stem_bottom_radius: float = 9.0  # shared by every piece
    stem_curve: float = 0.6  # 0 = straight taper, 1 = strongly concave
    stem_overlap: float = 0.5  # stem runs this far into base and shoulder
    stem_samples: int = 12
    shoulder_height: float = 3.0
    back_row_shoulder_z: float = 13.0
    pawn_shoulder_z: float = 11.0
    pin_socket_diameter: float = 8.3  # locating-pin socket in the base
    pin_socket_depth: float = 5.0  # 0 leaves the base solid
    bevel_clearance: float = 0.3  # bevels stop this far above a seated edge

    def stem_profile(self, stem_top_radius: float, shoulder_z: float) -> List[Point]:
        """(radius, z) points of the concave stem, base top to shoulder."""
        z0 = self.base_height
        control_z = z0 + (1 - self.stem_curve) * (shoulder_z - z0)
        return quadratic_bezier(
            (self.stem_bottom_radius, z0 - self.stem_overlap),
            (stem_top_radius, control_z),
            (stem_top_radius, shoulder_z + self.stem_overlap),
            self.stem_samples,
        )

    def problems(self) -> List[str]:
        problems = _positive(
            self,
            exempt=("pin_socket_depth", "stem_curve", "stem_samples", "stem_overlap"),
        )
        if problems:
            return problems
        if not 0 <= self.stem_curve <= 1:
            problems.append("stem_curve must be between 0 and 1")
        if self.stem_samples < 2:
            problems.append("stem_samples must be at least 2")
        if not 0 <= self.stem_overlap < self.base_height:
            problems.append("stem_overlap must be shorter than the base")
        if 2 * self.base_round >= self.base_height:
            problems.append("base_round is too large for the base height")
        if self.stem_bottom_radius >= self.base_radius - self.base_round:
            problems.append("stem must start inside the rounded base top")
        if self.edge_round >= self.shoulder_height / 2:
            problems.append("edge_round is too large for the shoulder")
        for name in ("pawn_shoulder_z", "back_row_shoulder_z"):
            if getattr(self, name) <= self.base_height + self.stem_overlap:
                problems.append(f"{name} must be above the base")
        if self.pin_socket_depth < 0:
            problems.append("pin_socket_depth must not be negative")
        elif self.pin_socket_depth >= self.base_height:
            problems.append("pin socket must stay inside the base")
        if self.pin_socket_diameter >= 2 * self.stem_bottom_radius:
            problems.append("pin socket must be narrower than the stem")
        return problems


def _stem_problems(stem_top_radius: float, body: ChessBodyDimensions) -> List[str]:
    if stem_top_radius > body.stem_bottom_radius:
        return ["stem top must not be wider than the stem bottom"]
    return []


def _shoulder_problems(
    stem_top_radius: float, shoulder_radius: float, body: ChessBodyDimensions
) -> List[str]:
    problems = _stem_problems(stem_top_radius, body)
    if shoulder_radius - body.edge_round <= stem_top_radius:
        problems.append("shoulder must overhang the stem by more than edge_round")
    if shoulder_radius > body.base_radius:
        problems.append("shoulder must not be wider than the base")
    return problems


@dataclass(frozen=True)
class PawnDimensions(_Validated):
    stem_top_radius: float = 4.0
    shoulder_radius: float = 8.0
    ball_radius: float = 7.5

    def ball_center_above_shoulder(self) -> float:
        """Ball sunk so its flat on the shoulder is as wide as the stem top."""
        return math.sqrt(self.ball_radius**2 - self.stem_top_radius**2)

    def problems(self) -> List[str]:
        problems = _positive(self)
        if self.ball_radius <= self.stem_top_radius:
            problems.append("ball must be wider than the stem top")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        return _shoulder_problems(self.stem_top_radius, self.shoulder_radius, body)


@dataclass(frozen=True)
class RookDimensions(_Validated):
    """Square castle head sitting at shoulder height (no separate shoulder)."""

    stem_top_radius: float = 7.5
    head_width: float = 22.0
    head_height: float = 15.0
    crenel_width: float = 7.0
    crenel_depth: float = 5.0
    cross_crenels: bool = True  # "+" (four merlons); False cuts a single "-"

    def problems(self) -> List[str]:
        problems = _positive(self)
        if self.crenel_width >= self.head_width:
            problems.append("crenels must be narrower than the head")
        if self.crenel_depth >= self.head_height:
            problems.append("crenels must be shallower than the head")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        problems = _stem_problems(self.stem_top_radius, body)
        if self.head_width / 2 <= self.stem_top_radius:
            problems.append("castle head must overhang the stem")
        return problems


# Knight head outline in the XZ plane, z measured up from the shoulder top:
# back of the head with two mane notches, ear, face, snubbed snout, flat jaw.
KNIGHT_OUTLINE: Tuple[Point, ...] = (
    (-10.01, 0.0),
    (-6.92, 12.71),
    (-4.41, 13.07),
    (-6.32, 14.3),
    (-5.73, 15.86),
    (-3.23, 16.22),
    (-5.14, 17.42),
    (-4.09, 20.15),
    (14.56, 4.16),
    (14.56, 0.0),
)


@dataclass(frozen=True)
class KnightDimensions(_Validated):
    """Flat, bevelled head slab standing on a round shoulder."""

    stem_top_radius: float = 5.5
    shoulder_radius: float = 10.0
    head_outline: Tuple[Point, ...] = KNIGHT_OUTLINE
    head_thickness: float = 8.0
    bevel: float = 0.7
    eye_diameter: float = 2.6
    eye_center: Point = (1.4, 10.1)
    eye_depth: float = 1.0  # dimple on each face

    def shortest_outline_edge(self) -> float:
        pts = self.head_outline
        return min(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))

    def problems(self) -> List[str]:
        problems = _positive(self)
        if len(self.head_outline) < 3:
            problems.append("head outline needs at least three points")
            return problems
        if 2 * self.bevel >= self.shortest_outline_edge():
            problems.append("bevel would consume the shortest head-outline edge")
        if 2 * self.bevel >= self.head_thickness:
            problems.append("bevel is too large for the head thickness")
        if 2 * self.eye_depth >= self.head_thickness:
            problems.append("eye dimples would meet in the middle")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        problems = _shoulder_problems(self.stem_top_radius, self.shoulder_radius, body)
        if max(abs(x) for x, _ in self.head_outline) > body.base_radius:
            problems.append("knight head must not reach past the base")
        return problems


@dataclass(frozen=True)
class BishopDimensions(_Validated):
    """Revolved head growing from the stem-top width, oblong finial, mitre slit."""

    stem_top_radius: float = 5.0
    shoulder_radius: float = 10.5
    # Head profile (radius, height above shoulder) after its start at the
    # stem-top radius: control points of the lower and upper cubic Beziers.
    head_lower: Tuple[Point, Point, Point] = ((6.0, 5.0), (7.7, 8.6), (7.7, 12.2))
    head_upper: Tuple[Point, Point, Point] = ((7.7, 18.0), (3.4, 21.6), (0.0, 22.3))
    curve_samples: int = 16
    finial_radius: float = 3.0
    finial_half_height: float = 4.0
    finial_center: float = 21.6  # above the shoulder top
    slit: bool = True
    slit_width: float = 1.4
    slit_angle: float = 40.0  # degrees below horizontal, falling toward +X
    slit_inner: Point = (-1.7, 16.5)  # where the cut stops, past the centre line
    slit_outer_x: float = 12.0  # far enough out to clear the head

    def head_curves(self) -> Tuple[Cubic, Cubic]:
        lower: Cubic = ((self.stem_top_radius, 0.0), *self.head_lower)
        upper: Cubic = (self.head_lower[-1], *self.head_upper)
        return lower, upper

    def head_profile(self) -> List[Point]:
        lower, upper = self.head_curves()
        return (
            cubic_bezier(lower, self.curve_samples)
            + cubic_bezier(upper, self.curve_samples)[1:]
        )

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("curve_samples",))
        if self.curve_samples < 2:
            problems.append("curve_samples must be at least 2")
        if self.head_upper[-1][0] != 0:
            problems.append("head profile must close on the axis")
        if not 0 < self.slit_angle < 90:
            problems.append("slit_angle must be between 0 and 90 degrees")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        return _shoulder_problems(self.stem_top_radius, self.shoulder_radius, body)


@dataclass(frozen=True)
class QueenDimensions(_Validated):
    """Short neck under a flared crown with radial V notches (no ball)."""

    stem_top_radius: float = 6.0
    shoulder_radius: float = 11.0
    neck_radius: float = 3.5
    neck_height: float = 4.0
    crown_offset: float = 3.0  # crown starts this far above the shoulder top
    crown_base_radius: float = 5.0
    crown_top_radius: float = 10.0
    crown_height: float = 18.0
    notch_count: int = 8
    notch_width: float = 4.0
    notch_depth: float = 5.0
    notch_overcut: float = 0.5
    notch_inner_radius: float = 4.5
    notch_length: float = 8.0
    notch_phase: float = 22.5  # degrees

    def problems(self) -> List[str]:
        problems = _positive(self, exempt=("notch_phase",))
        if self.crown_offset >= self.neck_height:
            problems.append("crown must start on the neck")
        if self.crown_base_radius < self.neck_radius:
            problems.append("crown must not be narrower than the neck")
        if self.notch_depth >= self.crown_height:
            problems.append("notches must be shallower than the crown")
        if self.notch_inner_radius + self.notch_length <= self.crown_top_radius:
            problems.append("notches must break through the crown rim")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        return _shoulder_problems(self.stem_top_radius, self.shoulder_radius, body)


@dataclass(frozen=True)
class KingDimensions(_Validated):
    """Round head with a filleted top under a flat, bevelled cross."""

    stem_top_radius: float = 5.5
    shoulder_radius: float = 11.0
    head_radius: float = 8.0
    head_height: float = 11.0
    head_fillet: float = 1.5
    cross_thickness: float = 5.0
    bar_width: float = 5.0
    bar_height: float = 17.0
    arm_span: float = 12.0
    arm_height: float = 5.0
    arm_offset: float = 7.0  # arm bottom above the bar bottom
    cross_embed: float = 0.5  # cross sinks into the head top
    bevel: float = 0.8

    def problems(self) -> List[str]:
        problems = _positive(self)
        if self.arm_offset + self.arm_height >= self.bar_height:
            problems.append("cross arms must sit below the top of the bar")
        if self.arm_span <= self.bar_width:
            problems.append("cross arms must reach past the bar")
        if 2 * self.bevel >= min(self.cross_thickness, self.bar_width, self.arm_height):
            problems.append("bevel is too large for the cross")
        if self.head_fillet >= min(self.head_radius, self.head_height):
            problems.append("head_fillet is too large for the head")
        if self.cross_embed >= self.head_fillet:
            problems.append("cross_embed must stay within the flat head top")
        return problems

    def body_problems(self, body: ChessBodyDimensions) -> List[str]:
        return _shoulder_problems(self.stem_top_radius, self.shoulder_radius, body)
