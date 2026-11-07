"""Real CAD assembly, exploded and display-only cutaway review boards."""

import argparse
import json
from pathlib import Path
from typing import List, Sequence

from PIL import Image, ImageDraw
from render_drivetrain_groups import INK, MUTED, canvas, font

from efficio import preview, renderer
from efficio.examples.resin_engine import resin_engine_assembly, resin_engine_geometry
from efficio.inspection import inspect_parts
from efficio.objects.assembly import PreviewPart

CLEAR = {"resin_jacket", "resin_oil_pan"}


def render(parts: Sequence[PreviewPart], width: int, height: int) -> Image.Image:
    """Clear-material candidates shown as wire outlines, not optical simulation."""
    all_triangles = renderer.tessellate_parts(parts)
    opaque = renderer.tessellate_parts([p for p in parts if p[0] not in CLEAR])
    # Degenerate triangles supply identical framing without painting surfaces.
    fit = [((t[0], t[0], t[1]), c) for t, c in all_triangles]
    image = renderer.create_color_view(
        opaque + fit,
        preview.ISOMETRIC,
        style=renderer.PreviewStyle(panel_width=width, panel_height=height, margin=45),
        show_grid=False,
    )
    viewport = preview.Viewport.fit(
        (preview.ISOMETRIC.project(p)[:2] for t, _ in all_triangles for p in t),
        width,
        height,
        45,
    )
    draw = ImageDraw.Draw(image, "RGBA")
    for name, solid, color in parts:
        if name not in CLEAR:
            continue
        for edge in solid.Edges():
            points = []
            for i in range(17):
                p = edge.positionAt(i / 16)
                x, y, _ = preview.ISOMETRIC.project((p.x, p.y, p.z))
                points.append(viewport.to_pixels(x, y))
            draw.line(points, fill=(*color, 170), width=2)
    return image


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    a = resin_engine_assembly(30)
    parts = a.preview_parts()
    image = canvas(
        "Educational resin engine / separate-part assembly",
        "Actual CAD | Continuous opaque liners | Clear candidates shown as outlines, not optical rendering",
        1440,
    )
    image.paste(render(parts, 1720, 850), (40, 120))
    draw = ImageDraw.Draw(image)
    entries = [
        (
            "Blue",
            "Four removable, flanged cylinder liners — full circumferential walls",
        ),
        ("Green", "Liner deck and connecting rods; yellow pistons inside the liners"),
        ("Red / purple", "Head, end bearing supports and lower bearing frame"),
        (
            "Pale outlines",
            "Separate coolant jacket and oil pan: candidate clear resin parts",
        ),
    ]
    for i, (label, text) in enumerate(entries):
        draw.text((50, 1000 + i * 55), f"{label}: {text}", font=font(23), fill=INK)
    draw.text(
        (50, 1250),
        "30 mm bore / 26 mm stroke / 40 mm pitch. Displayed at 30 degrees crank angle.",
        font=font(23),
        fill=INK,
    )
    draw.text(
        (50, 1300),
        "Fluid circulation is undecided. Ports are open; fittings, seals, pumps and galleries are not implemented.",
        font=font(21),
        fill=MUTED,
    )
    draw.text(
        (50, 1340),
        "Standalone engine proposal: gearbox mounting and resin/metal bearing interfaces still require design.",
        font=font(21),
        fill=MUTED,
    )
    image.save(output / "07-resin-engine-assembled.png")
    exploded: List[PreviewPart] = []
    for name, solid, color in parts:
        offset = (0.0, 0.0, 0.0)
        if name == "resin_head":
            offset = (0, 0, 100)
        elif name == "resin_deck":
            offset = (0, 0, 65)
        elif name.startswith("resin_liner_"):
            offset = (0, 0, 30)
        elif name == "resin_jacket":
            offset = (85, 0, 15)
        elif name == "resin_front_support":
            offset = (0, -45, 0)
        elif name == "resin_rear_support":
            offset = (0, 45, 0)
        elif name == "resin_bearing_frame":
            offset = (0, 0, -35)
        elif name == "resin_oil_pan":
            offset = (85, 0, -65)
        exploded.append((name, solid.translate(offset), color))
    image = canvas(
        "Educational resin engine / exploded parts",
        "Display translations only | Candidate assembly boundaries, not a proven installation sequence",
        1500,
    )
    image.paste(render(exploded, 1720, 1070), (40, 120))
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(
        [
            "Top to bottom: head → liner deck → four liners → crank mechanism → lower bearing frame.",
            "End bearing supports pull apart; jacket and oil pan are offset to the right.",
            "Mold concept: axial liner cores; removable cavity cores for open-top jacket and pan.",
            "Unresolved: draft, parting seams, port cores/drilling, seal grooves, clamps, shrinkage and bore finishing.",
        ]
    ):
        draw.text(
            (50, 1230 + i * 55), line, font=font(22), fill=INK if i < 2 else MUTED
        )
    image.save(output / "08-resin-engine-exploded.png")
    housing = [p for p in parts if p[0].startswith("resin_")]
    moving = [p for p in parts if not p[0].startswith("resin_")]
    cut = inspect_parts(housing, axis="X", position=0.0) + moving
    image = canvas(
        "Educational resin engine / display cutaway and system intent",
        "Housing clipped at local X = 0 for this image only | Moving parts uncut | Manufactured liners stay whole",
        1500,
    )
    image.paste(render(cut, 1720, 780), (40, 120))
    draw = ImageDraw.Draw(image)
    draw.text(
        (50, 935),
        "COOLING — conceptual external loop; the jacket cavity and two port bores exist in CAD",
        font=font(23),
        fill=(40, 115, 155),
    )
    draw.text(
        (50, 985),
        "Proposed pump → lower jacket port → space outside liners → upper port → proposed radiator",
        font=font(22),
        fill=INK,
    )
    draw.text(
        (50, 1065),
        "LUBRICATION — conceptual routing; only the pan cavity and drain bore exist in CAD",
        font=font(23),
        fill=(160, 110, 25),
    )
    draw.text(
        (50, 1115),
        "Proposed sump pickup → pump/filter → bearings / cylinder lubrication → gravity return",
        font=font(22),
        fill=INK,
    )
    for i, line in enumerate(
        [
            "No drilled crank oilways, fitted piston rings, valves, seals, pumps or radiator are modeled.",
            "Continuous liners keep proposed coolant outside the piston-running surfaces; liner seals remain unresolved.",
            "No claim of leak-tightness, structural strength, casting feasibility, printability or working circulation.",
        ]
    ):
        draw.text((50, 1225 + i * 55), line, font=font(21), fill=MUTED)
    image.save(output / "09-resin-engine-cutaway-systems.png")
    data = {
        "geometry_parameters": {
            k: v for k, v in vars(resin_engine_geometry()).items() if k != "engine"
        },
        "parts": [
            {
                "name": p.label,
                "owner": p.owner.path(),
                "valid": p.solid.isValid(),
                "solids": len(p.solid.Solids()),
                "volume_mm3": p.solid.Volume(),
            }
            for p in a.all_instances()
        ],
        "bom": a.bom_rows(),
        "totals": a.bom_totals(),
        "interferences_at_30": a.interferences(),
    }
    (output / "resin-engine-review.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Rendered and measured three resin-engine review boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("previews/resin-engine")
    )
    main(parser.parse_args().output_dir)
