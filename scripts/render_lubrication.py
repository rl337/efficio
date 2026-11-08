"""Efficio CAD views of modeled oil passages and explicitly missing loop elements."""

import argparse
import json
from pathlib import Path

from PIL import ImageDraw
from render_drivetrain_groups import INK, MUTED, canvas, font
from render_resin_engine import render

from efficio.examples.lubricated_engine import (
    lubricated_engine_assembly,
    lubrication_geometry,
)
from efficio.inspection import inspect_parts


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    a = lubricated_engine_assembly(30)
    g = lubrication_geometry()
    parts = a.preview_parts()
    housing = [p for p in parts if p[0].startswith("resin_")]
    rest = [p for p in parts if not p[0].startswith("resin_")]
    cut = inspect_parts(housing, axis="X", position=0) + rest
    image = canvas(
        "Educational engine / lubrication assembly",
        "Actual Efficio CAD | Clear pan shown as outline | Fluid operation and pump drive are undecided",
        1450,
    )
    image.paste(render(parts, 850, 850), (40, 150))
    image.paste(render(cut, 850, 850), (920, 150))
    draw = ImageDraw.Draw(image)
    draw.text(
        (55, 115),
        "Assembled — cylinder walls remain continuous",
        font=font(23),
        fill=INK,
    )
    draw.text((935, 115), "Display-only housing cutaway", font=font(23), fill=INK)
    for i, line in enumerate(
        [
            "The clear-pan candidate now rises to the liner base and surrounds the crankcase.",
            "Amber: pickup, longitudinal supply gallery, four under-liner outlets and two bearing-face outlets.",
            "The piston/rod/crank solids and coolant jacket are unchanged. No oil holes were cut through the liners.",
            "Open shaft exits, rail notches, service holes and drain require seals, clamps and closure design.",
            "No pump, filter, relief valve, strainer or drilled crank oilways are modeled; this is not an operating oil system.",
        ]
    ):
        draw.text(
            (50, 1050 + i * 65),
            line,
            font=font(22 if i < 3 else 20),
            fill=INK if i < 3 else MUTED,
        )
    image.save(output / "10-lubrication-assembly-cutaway.png")
    isolated = [p for p in parts if p[0].startswith("oil_") or p[0] == "resin_oil_pan"]
    image = canvas(
        "Oil pickup and distribution / modeled versus proposed",
        "Actual hollow CAD passages | 3 mm bore / 5 mm outside diameter | Direction arrows are explanatory",
        1550,
    )
    image.paste(render(isolated, 1720, 830), (40, 120))
    draw = ImageDraw.Draw(image)
    draw.text(
        (50, 970),
        "Pickup: open intake 2 mm above the floor → external suction port (lower service tube)",
        font=font(23),
        fill=(164, 112, 20),
    )
    draw.text(
        (50, 1015),
        "Pressure port (upper service tube) → gallery → four liner/skirt outlets + two bearing-face outlets",
        font=font(22),
        fill=(164, 112, 20),
    )
    labels = [
        "Pan / pickup",
        "PUMP + FILTER\nNOT MODELED",
        "Supply gallery",
        "Outlet jets / wetting",
        "Gravity return\nNOT SIMULATED",
    ]
    for i, label in enumerate(labels):
        x = 50 + i * 345
        draw.rounded_rectangle(
            (x, 1100, x + 300, 1190),
            radius=10,
            fill=(248, 236, 205) if i not in (1, 4) else (226, 231, 238),
            outline=MUTED,
            width=2,
        )
        draw.multiline_text((x + 12, 1120), label, font=font(19), fill=INK, spacing=5)
        if i < 4:
            for start in range(x + 305, x + 335, 8):
                draw.line((start, 1145, start + 4, 1145), fill=MUTED, width=2)
            draw.polygon(
                [(x + 337, 1145), (x + 329, 1140), (x + 329, 1150)], fill=MUTED
            )
    for i, line in enumerate(
        [
            "Two separate connected bore networks exist. The missing external pump deliberately breaks the complete loop.",
            "Bearing outlets stop at the bearing faces: shield compatibility and actual bearing feeds remain unresolved.",
            "Liner outlets aim into the lower bore; spray, wetting, oil demand and pressure have not been simulated or tested.",
            "Curved tube cores/fittings, material compatibility, assembly supports and leak-tight joints need engineering.",
        ]
    ):
        draw.text((50, 1250 + i * 55), line, font=font(20), fill=MUTED)
    image.save(output / "11-lubrication-paths.png")
    data = {
        "pickup_path": g.pickup_path(),
        "supply_paths": g.supply_paths(),
        "pickup_bore_solids": len(g.pickup().bore_solid().Solids()),
        "supply_bore_solids": len(g.supply().bore_solid().Solids()),
        "interferences_at_30": a.interferences(),
        "bom": a.bom_rows(),
        "totals": a.bom_totals(),
        "parts": [
            {
                "name": p.label,
                "valid": p.solid.isValid(),
                "solids": len(p.solid.Solids()),
            }
            for p in a.all_instances()
        ],
    }
    (output / "lubrication-review.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Rendered lubrication assembly and passage review boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("previews/lubrication"))
    main(parser.parse_args().output_dir)
