"""Exact boundary-distance checks for a deliberately restricted contour family.

Only circles, rectangles and capsules are certified. Arbitrary splines/concave
waists fail closed: sampling their edges is not a minimum-width proof.
"""

import math

import cadquery as cq


def convex_width(wire: cq.Wire) -> float:
    edges = wire.Edges()
    lines = [e for e in edges if e.geomType() == "LINE"]
    arcs = [e for e in edges if e.geomType() == "CIRCLE"]
    area = cq.Face.makeFromWires(wire).Area()
    if len(edges) == 1 and len(arcs) == 1:
        r = arcs[0].radius()
        if math.isclose(area, math.pi * r * r, rel_tol=1e-8):
            return 2 * r
    if len(edges) == 4 and len(lines) == 4:
        lengths = sorted(e.Length() for e in lines)
        # Rectangle area equals the product of adjacent side lengths; valid
        # quadrilaterals with these opposite lengths attain it only with right angles.
        if (
            math.isclose(lengths[0], lengths[1], rel_tol=1e-8)
            and math.isclose(lengths[2], lengths[3], rel_tol=1e-8)
            and math.isclose(area, lengths[0] * lengths[2], rel_tol=1e-8)
        ):
            return lengths[0]
    if len(edges) == 4 and len(lines) == 2 and len(arcs) == 2:
        r, length = arcs[0].radius(), lines[0].Length()
        if (
            all(
                math.isclose(a.radius(), r, rel_tol=1e-8)
                and math.isclose(a.Length(), math.pi * r, rel_tol=1e-8)
                for a in arcs
            )
            and math.isclose(lines[1].Length(), length, rel_tol=1e-8)
            and math.isclose(area, 2 * r * length + math.pi * r * r, rel_tol=1e-8)
        ):
            return 2 * r
    raise ValueError(
        "cannot certify minimum sealing width: boundary is not a supported circle, rectangle or capsule (concave/narrow-waist and spline faces require a stronger solver)"
    )


def measure_band_width(face: cq.Face) -> tuple[float, str]:
    holes = face.innerWires()
    if not holes:
        raise ValueError(
            "cannot certify sealing band without an explicitly enclosed opening"
        )
    outer = face.outerWire()
    candidates = [(convex_width(outer), "outer contour width")]
    for i, hole in enumerate(holes):
        convex_width(hole)
        candidates.append((outer.distance(hole), f"outer boundary / opening {i}"))
        for j, other in enumerate(holes[:i]):
            candidates.append((hole.distance(other), f"opening {j} / opening {i}"))
    return min(candidates)
