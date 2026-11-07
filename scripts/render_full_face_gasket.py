"""Full-face gasket coverage and actual residual face-gap geometry."""

import argparse
import json
from pathlib import Path
from typing import cast

import cadquery as cq
from PIL import Image, ImageDraw
from render_drivetrain_groups import INK, canvas, font
from render_resin_engine import render

from efficio import preview, renderer
from efficio.examples.gasket_review import full_face_pump_review, pump_gasket_review
from efficio.objects.assembly import PreviewPart
from efficio.objects.base import EfficioObject
from efficio.objects.gaskets.face import extrude
from efficio.objects.pumps.blind_support import BlindSupportPart
from efficio.objects.pumps.external_gear import GearPumpGeometry


def solid(obj: EfficioObject) -> cq.Shape:
    shape = obj.shape()
    assert shape is not None
    return cast(cq.Shape, shape.workplane().val())


def plan(parts: list[PreviewPart], width: int = 840, height: int = 740) -> Image.Image:
    return renderer.create_color_view(
        renderer.tessellate_parts(parts),
        preview.View("XY", (0, 0, 1), (0, 1, 0)),
        style=renderer.PreviewStyle(panel_width=width, panel_height=height, margin=40),
        show_grid=False,
    )


def labels(board: Image.Image, lines: list[str], y: int = 950) -> None:
    draw = ImageDraw.Draw(board)
    for i, line in enumerate(lines):
        draw.text((50, y + i * 52), line, font=font(21), fill=INK)


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    old_body, old = pump_gasket_review()
    body, design = full_face_pump_review()
    g = GearPumpGeometry(**vars(body.d.pump))
    face = body.gasket_faces()["cover_seal"]
    housing, free = solid(body), solid(design.free)
    cover = solid(BlindSupportPart(body.d, "cover"))
    board = canvas(
        "Full-face gasket / seal the nose regions",
        "Actual top views | Orange: free gasket | Housing and cavity remain visible",
        1400,
    )
    board.paste(
        plan(
            [
                ("old body", solid(old_body), (72, 144, 170)),
                ("old gasket", solid(old.free), (235, 147, 55)),
            ]
        ),
        (40, 140),
    )
    board.paste(
        plan(
            [("body", housing, (72, 144, 170)), ("full gasket", free, (235, 147, 55))]
        ),
        (920, 140),
    )
    labels(
        board,
        [
            "LEFT: earlier oval gasket. It did not cover the two central nose/wedge regions.",
            "RIGHT: generated from the actual full mating face, retaining the figure-eight cavity and all four bolt openings.",
            "The new band extends over both noses. Sharp tips are explicitly rounded; CAD width lower bound: 2 mm.",
            "0.7 mm hard lands remain beside the cavity, bolt holes and exterior; gasket has a further 0.4 mm inset.",
            "The old groove was already separated from water by solid land; there was no modeled open groove bypass.",
            "This improves face coverage. It does not eliminate gear end-gap or meshing leakage.",
        ],
    )
    board.save(output / "30-full-face-gasket-comparison.png")
    board = canvas(
        "Declared mating face / separate gasket and cover",
        "Actual CAD | Cyan: recess floor | Orange: generated free gasket | Exploded displacement only",
        1400,
    )
    marker = extrude(face.face, 0.015, face.normal)
    board.paste(
        render(
            [("body", housing, (72, 144, 170)), ("face", marker, (30, 220, 205))],
            840,
            790,
        ),
        (40, 140),
    )
    board.paste(
        render(
            [
                ("body", housing, (72, 144, 170)),
                ("gasket", free.translate((0, 0, 9)), (235, 147, 55)),
                ("cover", cover.translate((0, 0, 22)), (157, 182, 195)),
            ],
            840,
            790,
        ),
        (920, 140),
    )
    labels(
        board,
        [
            "Full-face source has one known wet-cavity opening and four known bolt openings; unknown topology is rejected.",
            "Free thickness 1.05 mm / recess depth 1.00 mm: provisional 4.76% squeeze, not a qualified silicone specification.",
            "Ports move down 0.70 mm to preserve a 2.08 mm roof below the deeper seat. Chamber and gear positions stay fixed.",
            "Hard closure lands retain the original cover plane and 0.08 mm rotor end clearance.",
            f"Explicit corner/tip rounding removes {design.rounded_area_loss:.3f} mm2 of gasket footprint; no keep-out is cut away.",
            "Mold release, flatness, material compatibility, compression recovery and leak-tightness remain unqualified.",
        ],
    )
    board.save(output / "31-full-face-declaration-and-exploded.png")
    gap = g.cavity().intersect(
        cq.Solid.makeBox(
            100,
            100,
            g.face_clearance / 2,
            cq.Vector(-40, -50, g.depth - g.face_clearance / 2),
        )
    )
    board = canvas(
        "Remaining leakage / inside the wet cavity",
        "Red: an actual connected fluid-space slice above the rotors | Not simulated flow or a pressure prediction",
        1400,
    )
    board.paste(
        plan(
            [
                ("body", housing, (72, 144, 170)),
                ("seal", design.installed_estimate, (68, 188, 110)),
                ("running gap", gap, (215, 82, 98)),
            ]
        ),
        (40, 140),
    )
    crop = cq.Solid.makeBox(0.04, 6, 2, cq.Vector(-0.02, 10.5, g.depth - 1.5))
    section = [
        ("body", housing.intersect(crop), (72, 144, 170)),
        ("cover", cover.intersect(crop), (157, 182, 195)),
        ("installed gasket", design.installed_estimate.intersect(crop), (68, 188, 110)),
        ("gap", gap.intersect(crop), (215, 82, 98)),
    ]
    picture = renderer.create_color_view(
        renderer.tessellate_parts(section),
        preview.View("YZ", (1, 0, 0), (0, 0, 1)),
        style=renderer.PreviewStyle(panel_width=840, panel_height=740, margin=40),
        show_grid=False,
    )
    board.paste(picture, (920, 140))
    labels(
        board,
        [
            "LEFT: the red upper running-gap slice is one connected volume across both port sides; gears lie below it.",
            "RIGHT: magnified section at x=0. Green: estimated installed gasket outside the cavity; the red internal gap remains.",
            "No geometric seal separates inlet and outlet across this entire top gap. Actual leakage rate has not been measured.",
            "Tip clearance, backlash, shaft leakage and trapped-fluid behavior also require separate pump-design work.",
            "Do not remove the running clearance or extend silicone over rotating teeth to hide this issue.",
            "Next hydraulic work: selected bearing/end-face materials, tolerances and bench flow-versus-head testing.",
        ],
    )
    board.save(output / "32-full-face-residual-leakage.png")
    bore_probe = cq.Solid.makeCylinder(
        g.port_radius - 0.01,
        75.98,
        cq.Vector(g.centres / 2, -37.99, g.port(1)[2]),
        cq.Vector(0, 1, 0),
    )
    port_obstruction = housing.intersect(bore_probe).Volume()
    if port_obstruction > 1e-7:
        raise ValueError("lowered side/terminal bore is obstructed")
    artifacts = {
        "full_face_body": housing,
        "full_face_cover": cover,
        "full_face_gasket_free": free,
        "full_face_installed_estimate": design.installed_estimate,
        "full_face_clearance_envelope": design.clearance_envelope,
        "full_face_recess": design.recess_envelope,
        "residual_top_gap_slice": gap,
    }
    validity = {}
    for name, value in artifacts.items():
        path = output / (name + ".step")
        cq.exporters.export(value, str(path))
        imported = cq.importers.importStep(str(path)).val()
        assert isinstance(imported, cq.Shape)
        validity[name] = imported.isValid()
        if not validity[name]:
            raise ValueError("invalid STEP reimport")
    measurements = {
        "minimum_width_lower_bound_mm": design.minimum_width,
        "width_method": design.limiting_boundaries,
        "rounded_area_loss_mm2": design.rounded_area_loss,
        "free_thickness_mm": design.free.thickness,
        "closed_height_mm": face.closed_height,
        "squeeze_fraction": design.squeeze_fraction,
        "gland_fill_fraction": design.gland_fill_fraction,
        "estimated_spread_mm": design.estimated_spread,
        "hard_land_mm": body.full_face_land,
        "stop_planes_checked": design.stop_planes_checked,
        "opening_names": [o.name for o in face.openings],
        "free_cavity_clearance_mm": free.distance(face.keepouts[0].solid),
        "clearance_envelope_cavity_mm": design.clearance_envelope.distance(
            face.keepouts[0].solid
        ),
        "port_axis_z_mm": g.port(1)[2],
        "port_body_obstruction_mm3": port_obstruction,
        "port_roof_mm": body.d.wall_measurements()["port_roof_to_gasket"],
        "top_gap_slice_connected_solids": len(gap.Solids()),
        "top_gap_slice_volume_mm3": gap.Volume(),
        "step_reimports_valid": validity,
    }
    (output / "full-face-measurements.json").write_text(
        json.dumps(measurements, indent=2)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
