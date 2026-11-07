"""Render actual declared faces and generated gasket artifacts through Efficio."""

import argparse
import json
from pathlib import Path
from typing import cast

import cadquery as cq
from PIL import ImageDraw
from render_drivetrain_groups import INK, canvas, font
from render_resin_engine import render

from efficio import preview, renderer
from efficio.examples.gasket_review import pump_gasket_review, rectangular_gasket_review
from efficio.objects.gaskets.face import extrude
from efficio.objects.pumps.blind_support import BlindSupportPart


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    body, design = pump_gasket_review()
    declaration = body.gasket_faces()["cover_seal"]
    body_shape = body.shape()
    assert body_shape is not None
    shape = cast(cq.Shape, body_shape.workplane().val())
    free = cast(cq.Shape, design.free.shape().workplane().val())
    cover_shape = BlindSupportPart(body.d, "cover").shape()
    assert cover_shape is not None
    cover = cast(cq.Shape, cover_shape.workplane().val())
    face_marker = extrude(declaration.face, 0.015, declaration.normal)
    board = canvas(
        "Gasket faces / wider pump proposal",
        "Actual CAD | Blue: housing; cyan: declared recess floor; orange: separate free-state gasket",
        1400,
    )
    board.paste(
        render(
            [("body", shape, (72, 144, 170)), ("face", face_marker, (30, 220, 205))],
            840,
            790,
        ),
        (40, 140),
    )
    board.paste(
        render(
            [
                ("body", shape, (72, 144, 170)),
                ("gasket", free.translate((0, 0, 8)), (235, 147, 55)),
                ("cover", cover.translate((0, 0, 20)), (157, 182, 195)),
            ],
            840,
            790,
        ),
        (920, 140),
    )
    draw = ImageDraw.Draw(board)
    lines = [
        "LEFT: named cover_seal face is selected from the actual machined body's recess floor.",
        "RIGHT: matching wider cover and generated free gasket, displaced only for this exploded view.",
        f"Measured minimum band: {design.minimum_width:.2f} mm. Rejection floor: 1 mm (configurable).",
        "Review recess: 3.0 mm wide x 0.30 mm deep; free gasket: 0.33 mm; boundary insets: 0.20 mm.",
        "Larger flange and relocated bolt bosses retain 2.65 mm groove-to-bolt ligament; cavity unchanged.",
        "9.1% nominal squeeze is an editable example, not a qualified compression or sealing specification.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 960 + i * 52), line, font=font(22), fill=INK)
    board.save(output / "27-gasket-face-and-generated-part.png")
    plate, other, other_design = rectangular_gasket_review()
    top = preview.View("seal plane", (0, 0, 1), (0, 1, 0))
    parts = [
        ("recess", design.recess_envelope, (120, 151, 165)),
        ("spread", design.clearance_envelope, (68, 188, 110)),
        ("free", free, (235, 147, 55)),
        ("wet", declaration.keepouts[0].solid, (99, 179, 227)),
    ]
    board = canvas(
        "Gasket clearance / explicit openings",
        "Actual CAD | Orange: free gasket; green: spread allowance; gray: recess; blue: wet cavity",
        1400,
    )
    board.paste(
        renderer.create_color_view(
            renderer.tessellate_parts(parts),
            top,
            style=renderer.PreviewStyle(panel_width=840, panel_height=760, margin=40),
            show_grid=False,
        ),
        (40, 140),
    )
    board.paste(
        render(
            [
                ("plate", plate, (72, 144, 170)),
                (
                    "free gasket",
                    cast(
                        cq.Shape, other_design.free.shape().workplane().val()
                    ).translate((0, 0, 4)),
                    (235, 147, 55),
                ),
            ],
            840,
            760,
        ),
        (920, 140),
    )
    draw = ImageDraw.Draw(board)
    lines = [
        "LEFT: wet cavity remains open; the full rotating-gear swept volumes are separate checked keep-outs.",
        f"Volume-conserving isotropic spread estimate: {design.estimated_spread:.4f} mm per edge; allowance multiplier: 1.25.",
        f"Estimated free gasket / recess volume: {100*design.gland_fill_fraction:.1f}%. Green is NOT a deformation simulation.",
        "RIGHT: second example derives a gasket from a rectangular plate with a cavity and two bolt openings.",
        "Every opening must be named explicitly. Unsupported widths, missing openings and collisions raise errors.",
        "Groove, hard closure and free/installed shapes are distinct. Material, mold release and seals remain unqualified.",
    ]
    for i, line in enumerate(lines):
        draw.text((50, 960 + i * 52), line, font=font(21), fill=INK)
    board.save(output / "28-gasket-clearance-and-flange.png")
    # Magnified true-scale section near the circular end of the gasket.
    crop = cq.Solid.makeBox(0.04, 5.5, 1.2, cq.Vector(-0.02, 11, 15.5))
    section_view = preview.View("section", (1, 0, 0), (0, 0, 1))
    board = canvas(
        "Gasket section / free and installed states",
        "True CAD section at x=0 | Same scale | Orange: free state; green: estimated installed state",
        1150,
    )
    for x, gasket, with_cover in [
        (40, free, False),
        (920, design.installed_estimate, True),
    ]:
        parts = [
            ("body", shape.intersect(crop), (72, 144, 170)),
            (
                "gasket",
                gasket.intersect(crop),
                (68, 188, 110) if with_cover else (235, 147, 55),
            ),
        ]
        if with_cover:
            parts.append(("cover", cover.intersect(crop), (157, 182, 195)))
        board.paste(
            renderer.create_color_view(
                renderer.tessellate_parts(parts),
                section_view,
                style=renderer.PreviewStyle(
                    panel_width=840, panel_height=620, margin=40
                ),
                show_grid=False,
            ),
            (x, 140),
        )
    draw = ImageDraw.Draw(board)
    for i, line in enumerate(
        [
            "LEFT: 0.33 mm free gasket stands 0.03 mm above the 0.30 mm recess; cover omitted.",
            "RIGHT: estimated installed gasket at hard closure. Body/cover lands meet; remaining side space is visible.",
            "In-plane width and through-thickness are separate settings. The 1 mm floor applies to band width only.",
            "Real silicone may spread unevenly. Moldability, compression recovery and sealing need material trials.",
        ]
    ):
        draw.text((50, 800 + i * 58), line, font=font(22), fill=INK)
    board.save(output / "29-gasket-free-and-installed-section.png")
    shapes = {
        "review_body": shape,
        "review_cover": cover,
        "gasket_free": free,
        "gasket_installed_estimate": design.installed_estimate,
        "gasket_clearance_envelope": design.clearance_envelope,
        "recess_envelope": design.recess_envelope,
        "rectangular_flange": plate,
        "rectangular_gasket_free": cast(
            cq.Shape, other_design.free.shape().workplane().val()
        ),
    }
    exports = {}
    for name, solid in shapes.items():
        path = output / (name + ".step")
        cq.exporters.export(solid, str(path))
        imported = cq.importers.importStep(str(path)).val()
        assert isinstance(imported, cq.Shape)
        exports[name] = imported.isValid()
        if not exports[name]:
            raise ValueError("invalid exported solid: " + name)
    measurements = {
        "minimum_band_mm": design.minimum_width,
        "limiting_boundaries": design.limiting_boundaries,
        "free_thickness_mm": design.free.thickness,
        "closed_height_mm": declaration.closed_height,
        "squeeze_fraction": design.squeeze_fraction,
        "stop_planes_checked": design.stop_planes_checked,
        "isotropic_spread_mm": design.estimated_spread,
        "gland_fill_fraction": design.gland_fill_fraction,
        "wet_clearance_mm": free.distance(declaration.keepouts[0].solid),
        "swept_clearance_mm": free.distance(declaration.keepouts[1].solid),
        "wall_measurements_mm": body.d.wall_measurements(),
        "groove_to_bolt_mm": 2.65,
        "valid_step_reimports": exports,
    }
    (output / "gasket-measurements.json").write_text(json.dumps(measurements, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
