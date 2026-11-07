"""Editable wider pump seal proposal; does not replace the existing wet end."""

from dataclasses import replace

import cadquery as cq

from efficio.examples.water_feature_pump import (
    water_hose_terminal,
    water_pump_dimensions,
    water_wall_policy,
)
from efficio.objects.gaskets import (
    GasketDesign,
    GasketFace,
    GasketParameters,
    Opening,
    OpeningRole,
)
from efficio.objects.pumps.blind_support import BlindSupportPart


def pump_gasket_review() -> tuple[BlindSupportPart, GasketDesign]:
    original = water_pump_dimensions()
    d = replace(
        original,
        pump=replace(original.pump, wall=16),
        gasket_width=3.0,
        exterior_offset=10.0,
    )
    # A wider groove needs both a larger flange and relocated bolt bosses.
    water_wall_policy().require(d.wall_measurements())
    ligament = d.pump.wall / 2 - d.pump.bolt_radius - d.gasket_inset - d.gasket_width
    if ligament < water_wall_policy().minimum_mm:
        raise ValueError("review groove consumes bolt ligament")
    body = BlindSupportPart(d, "body", water_hose_terminal(d), 12)
    return body, body.generate_gasket(
        "cover_seal",
        GasketParameters(
            free_thickness=0.33,
            outer_inset=0.2,
            inner_inset=0.2,
            minimum_width=1.0,
            spread_margin=1.25,
        ),
    )


def rectangular_gasket_review() -> tuple[cq.Shape, GasketFace, GasketDesign]:
    plate = (
        cq.Workplane("XY")
        .box(40, 30, 3)
        .faces(">Z")
        .workplane()
        .hole(12)
        .faces(">Z")
        .workplane()
        .pushPoints([(-14, 0), (14, 0)])
        .hole(3)
        .val()
    )
    assert isinstance(plate, cq.Shape)
    face = max(
        (f for f in plate.Faces() if f.geomType() == "PLANE"),
        key=lambda f: f.Center().z,
    )
    # This use site knows the drawing: one 12 mm opening and two 3 mm bolt holes.
    # Unknown dimensions/counts are rejected rather than classified heuristically.
    openings = []
    for wire in face.innerWires():
        edges = wire.Edges()
        if len(edges) != 1 or edges[0].geomType() != "CIRCLE":
            raise ValueError("review flange opening changed")
        radius = edges[0].radius()
        if abs(radius - 6) < 1e-7:
            openings.append(Opening("wet_cavity", wire, OpeningRole.WET_CAVITY))
        elif abs(radius - 1.5) < 1e-7:
            openings.append(
                Opening(
                    "bolt_left" if wire.Center().x < 0 else "bolt_right",
                    wire,
                    OpeningRole.BOLT,
                )
            )
        else:
            raise ValueError("review flange opening is unrecognized")
    if {o.name for o in openings} != {"wet_cavity", "bolt_left", "bolt_right"}:
        raise ValueError("review flange opening set changed")
    declared = GasketFace(
        face,
        tuple(openings),
        (),
        cq.Vector(0, 0, 1),
        0.3,
        "Example requires rigid closure 0.3 mm above plate face; mating lid/stops not generated",
    )
    return plate, declared, declared.generate(GasketParameters(0.31, 1, 1, 1.1))


def full_face_pump_review() -> tuple[BlindSupportPart, GasketDesign]:
    original = water_pump_dimensions()
    # Deeper gasket seat requires lowering the side drillings to retain roof.
    d = replace(
        original,
        pump=replace(original.pump, wall=16, port_drop=1.0),
        gasket_width=3.0,
        gasket_depth=1.0,
        exterior_offset=10.0,
        boss_radius=6.0,
    )
    water_wall_policy().require(d.wall_measurements())
    body = BlindSupportPart(
        d,
        "body",
        water_hose_terminal(d),
        12,
        gasket_style="full_face",
        full_face_land=0.7,
    )
    return body, body.generate_gasket(
        "cover_seal",
        GasketParameters(
            free_thickness=1.05,
            outer_inset=0.4,
            inner_inset=0.4,
            minimum_width=2.0,
            spread_margin=1.25,
            round_to_width=True,
        ),
    )
