"""Efficio pump assembly, exploded and actual passage review boards."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from render_drivetrain_groups import INK, MUTED, canvas, font
from render_resin_engine import render

from efficio import preview, renderer
from efficio.examples.pumped_engine import (
    external_lines,
    pump_geometry,
    pumped_engine_assembly,
)
from efficio.inspection import inspect_parts
from efficio.objects.assembly import PreviewPart
from efficio.objects.pumps.external_gear import gear_pump_assembly


def notes(image: Image.Image, lines: list[str], y: int) -> None:
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((50, y + 48 * i), line, font=font(21), fill=INK if i < 2 else MUTED)


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    a = pumped_engine_assembly(30)
    parts = a.preview_parts()
    image = canvas(
        "Crank-driven oil pump / engine integration",
        "Actual Efficio CAD | 30 degree crank pose | Prototype: no measured flow or pressure",
        1450,
    )
    image.paste(render(parts, 1720, 900), (40, 125))
    notes(
        image,
        [
            "Front-left: crank gear 18T → pump gear 22T (9/11 speed, opposite rotation); blue pump behind drive.",
            "Gray adapter bolts to a drilled front-support variant. Amber tubing leads to a removable coarse strainer.",
            "All four liners remain whole; pan and coolant jacket are outlined for visibility, not optically rendered.",
            "Open relief-valve interfaces, seals, fasteners, hose supports and filter mounting still require engineering.",
            "The CAD fits at sampled poses. No claim of sealed operation, casting feasibility, strength or engine oil delivery.",
        ],
        1080,
    )
    image.save(output / "12-pump-engine-assembly.png")

    g = pump_geometry()
    pump = gear_pump_assembly(g, 0)
    local = pump.preview_parts()
    cut = inspect_parts(
        [p for p in local if p[0] == "pump_body"],
        axis="Z",
        position=g.base + 0.1,
        mode="halfspace",
    )
    cut += [
        p
        for p in local
        if p[0]
        in {"pump_driver", "pump_idler", "pump_driver_shaft", "pump_idler_shaft"}
    ]
    exploded: list[PreviewPart] = []
    for name, solid, color in local:
        offset = (0, 0, 0)
        if name == "pump_cover":
            offset = (0, 0, 22)
        elif "rear_collar" in name:
            offset = (0, 0, -22)
        elif "collar" in name:
            offset = (0, 0, 32)
        elif name in {"pump_driver", "pump_idler"} or name.endswith("_pin"):
            offset = (0, 0, 8)
        elif "shaft" in name:
            offset = (0, 0, -15)
        exploded.append((name, solid.translate(offset), color))
    image = canvas(
        "Reusable external-gear pump / separate parts",
        "Module 1 · 12 + 12 teeth · 6 mm rotors | Exploded translations and display cutaway only",
        1500,
    )
    image.paste(render(exploded, 850, 950), (40, 150))
    image.paste(render(cut, 850, 950), (920, 150))
    draw = ImageDraw.Draw(image)
    draw.text(
        (55, 115),
        "Cover, collars, rotors, body and round-journal shafts",
        font=font(22),
        fill=INK,
    )
    draw.text(
        (935, 115),
        "Housing cut away to expose rotor arrangement",
        font=font(22),
        fill=INK,
    )
    notes(
        image,
        [
            "Four through-bolt interfaces clamp cover/body to the adapter; pinned rotors and removable collars retain round-journal shafts.",
            "Tip gap 0.15 mm; face gap 0.10 mm per side. These are editable candidates, not qualified resin tolerances.",
            "Seal counterbores are empty reservations. Face gasket, bearings, screws and axial retention need selected parts.",
            "No timed trapped-volume relief grooves yet: loaded operation needs pocket-volume analysis and a port-plate design.",
            "Use finish-machined faces and measured fits for the first bench unit; no pressure or flow rating is implied.",
        ],
        1160,
    )
    image.save(output / "13-pump-exploded.png")

    # Expose bores using the actual subtraction cores; geometry, not fluid dynamics.
    flow: list[PreviewPart] = []
    colors = {
        "pump_suction_line": (45, 145, 190),
        "pump_pressure_line": (219, 108, 45),
        "pump_delivery_line": (200, 145, 35),
    }
    for name, network in external_lines().items():
        flow.append((name + "_bore", network.bore_solid(), colors[name]))
    from efficio.examples.lubricated_engine import lubrication_geometry

    lg = lubrication_geometry()
    flow += [
        ("pickup_bore", lg.pickup().bore_solid(), (45, 145, 190)),
        ("gallery_bore", lg.supply().bore_solid(), (200, 145, 35)),
    ]
    flow += inspect_parts(
        [p for p in parts if p[0].startswith("oil_filter_")],
        axis="X",
        position=-70,
        mode="halfspace",
    )
    flow += [
        p
        for p in parts
        if p[0] in {"pump_body", "pump_driver", "pump_idler", "pickup_screen"}
    ]
    image = canvas(
        "Oil circuit / actual bores and explicit missing valve",
        "Blue: suction bore · orange: pressure bore · gold: delivery gallery | No flow simulation",
        1500,
    )
    image.paste(render(flow, 1720, 850), (40, 125))
    labels = ["Screened pickup", "Gear pump", "Coarse strainer", "Gallery / outlets"]
    draw = ImageDraw.Draw(image)
    for i, label in enumerate(labels):
        x = 50 + i * 440
        draw.rounded_rectangle(
            (x, 1010, x + 365, 1080),
            radius=8,
            fill=(234, 239, 244),
            outline=MUTED,
            width=2,
        )
        draw.text((x + 15, 1030), label, font=font(22), fill=INK)
        if i < 3:
            draw.line((x + 372, 1045, x + 423, 1045), fill=INK, width=3)
            draw.polygon([(x + 423, 1045), (x + 413, 1038), (x + 413, 1052)], fill=INK)
    notes(
        image,
        [
            "The two left-facing service ports are 12 mm apart: an external rated RELIEF VALVE IS NOT INSTALLED.",
            "Pressure takeoff is before the strainer; the separate return line reaches suction. The valve gap is not a fluid path.",
            "Pump side drillings reach tooth pockets. Rotating outer tooth-space transport is expected, not demonstrated.",
            "Pickup and strainer apertures are real; the strainer is highly restrictive and has no filtration rating.",
            "Bearing-face outlets remain external wetting provisions, not drilled crank feeds. Pan sealing is still unresolved.",
            "Bench gates: measured fits → leak check → freely returning low-speed flow → qualified relief / pressure mapping.",
        ],
        1140,
    )
    image.save(output / "14-pump-oil-paths.png")

    # A face-on view makes gear/port relationships legible without hiding housing.
    face = [
        p
        for p in local
        if p[0]
        not in {
            "pump_cover",
            "pump_driver_collar",
            "pump_idler_collar",
            "pump_driver_rear_collar",
            "pump_idler_rear_collar",
            "pump_driver_shaft",
            "pump_idler_shaft",
            "pump_driver_pin",
            "pump_idler_pin",
        }
    ]
    face = inspect_parts(
        [p for p in face if p[0] == "pump_body"],
        axis="Z",
        position=g.base + g.width / 2 + g.face_clearance,
    ) + [p for p in face if p[0] != "pump_body"]
    face += [
        ("suction_drilling_core", g.port_void(1), (45, 145, 190)),
        ("pressure_drilling_core", g.port_void(-1), (219, 108, 45)),
    ]
    top = preview.View("Pump XY", (0, 0, 1), (0, 1, 0))
    image = canvas(
        "Pump porting / direction and remaining hydraulic work",
        "View from +local Z; housing sectioned through ports | Blue/orange show actual drilling cores",
        1380,
    )
    panel = renderer.create_color_view(
        renderer.tessellate_parts(face),
        top,
        style=renderer.PreviewStyle(panel_width=1700, panel_height=800, margin=70),
        show_grid=False,
    )
    image.paste(panel, (50, 120))
    notes(
        image,
        [
            "At increasing engine crank angle: left rotor turns counterclockwise, right clockwise (in this local view).",
            "Upper local-Y port = suction; lower local-Y port = pressure. Fluid is carried around the two outer perimeters.",
            "The mesh separates inlet/outlet imperfectly: face gaps, tip gaps, backlash and shaft fits leak.",
            "Trapped tooth pockets can pressurize internally. External relief alone does not resolve an isolated mesh pocket.",
            "Before pressure testing: analyze pocket volume versus angle and design timed relief grooves / a replaceable face plate.",
            "Reversing the crank reverses the ports; this engine's filter/relief plumbing is configured for one direction.",
        ],
        1000,
    )
    image.save(output / "15-pump-porting.png")
    data = {
        "pump_dimensions": vars(g),
        "parts": [
            {
                "label": p.label,
                "part": p.part,
                "valid": p.solid.isValid(),
                "solids": len(p.solid.Solids()),
                "volume_mm3": p.solid.Volume(),
            }
            for p in a.all_instances()
        ],
        "bom": a.bom_rows(),
        "totals": a.bom_totals(),
        "interferences_at_30": a.interferences(),
        "relief_valve_installed": False,
        "measured_performance": None,
    }
    (output / "gear-pump-review.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Four Efficio pump review boards and geometry evidence written", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("previews/gear-pump"))
    main(parser.parse_args().output_dir)
