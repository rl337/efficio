"""Editorial physical groupings of the existing drivetrain occurrences.

Grouping changes ownership and preview colour only. It never rebuilds geometry,
changes poses, or adds hypothetical retention hardware. The five legacy sections
remain navigation groups; in particular Gearbox and Differential share support.
"""

from typing import Callable, List

from efficio.objects.assembly import Assembly, HardwareItem
from efficio.objects.base import Color


def _group(
    assembly: Assembly, name: str, choose: Callable[[str], bool], color: Color
) -> Assembly:
    return assembly.group_instances(
        name, [p.label for p in assembly.instances if choose(p.label)], color
    )


def _move_hardware(source: Assembly, target: Assembly, notes: List[str]) -> None:
    selected = [h for h in source.hardware if h.notes in notes]
    target.hardware.extend(selected)
    source.hardware = [h for h in source.hardware if h.notes not in notes]


def group_engine(assembly: Assembly, cylinders: int) -> None:
    housing = _group(
        assembly,
        "Housing",
        lambda n: n.startswith("engine_block") or n == "cylinder_head",
        (160, 60, 54),
    )
    _move_hardware(
        assembly,
        housing,
        ["Crank mains in block end walls", "Cylinder head", "Block split bolts"],
    )
    _group(
        assembly,
        "Crankshaft",
        lambda n: n.startswith("crank") and n != "crank_flywheel_stub",
        (218, 114, 45),
    )
    for index in range(cylinders):
        labels = {f"piston_{index}", f"connecting_rod_{index}", f"wrist_pin_{index}"}
        assembly.group_instances(
            f"Piston and rod {index + 1}", sorted(labels), (220, 164, 64)
        )
    _group(
        assembly,
        "Flywheel",
        lambda n: n in ("flywheel", "crank_flywheel_stub"),
        (135, 73, 130),
    )
    mounts = _group(
        assembly,
        "Engine mounts",
        lambda n: n.startswith("engine_mount"),
        (150, 115, 95),
    )
    _move_hardware(
        assembly,
        mounts,
        ["Engine mounts: through the gearbox plate and spacer into the block"],
    )


def group_gearbox(assembly: Assembly) -> None:
    _group(
        assembly, "Engine output adapter", lambda n: n == "crank_pinion", (206, 83, 50)
    )
    support = _group(
        assembly,
        "Gearbox support",
        lambda n: n.startswith("gearbox_plate") or n.startswith("gearbox_standoff"),
        (111, 128, 151),
    )
    _move_hardware(
        assembly,
        support,
        ["Carrier hubs in gearbox plates", "Gearbox standoff tie rods"],
    )
    shaft = _group(
        assembly,
        "Input shaft",
        lambda n: n in ("crown_gear", "input_pinion", "input_shaft"),
        (44, 139, 174),
    )
    _move_hardware(assembly, shaft, ["Input shaft in gearbox plates"])
    idler = _group(
        assembly,
        "Idler shaft",
        lambda n: n in ("idler_gear", "idler_shaft"),
        (66, 160, 122),
    )
    _move_hardware(assembly, idler, ["Idler shaft in gearbox plates"])


def group_differential(assembly: Assembly) -> None:
    _group(assembly, "Carrier", lambda n: n.startswith("diff_carrier"), (209, 147, 42))
    internals = _group(
        assembly,
        "Internal gears and pins",
        lambda n: n.startswith("diff_sun") or n.startswith("diff_planet"),
        (161, 103, 44),
    )
    _move_hardware(assembly, internals, ["Planet bolts"])


def group_sides(assembly: Assembly, component: str, colors: List[Color]) -> None:
    if len(colors) != 2:
        raise ValueError("Provide one color for each side")
    if any(h.quantity % 2 for h in assembly.hardware):
        raise ValueError("Paired hardware quantities must divide between the two sides")
    children = []
    for side, color in zip(("left", "right"), colors):
        children.append(
            assembly.group_instances(
                f"{side.title()} {component}",
                [p.label for p in assembly.instances if p.label.endswith("_" + side)],
                color,
            )
        )
    # These builders record paired bearings/fasteners, one equal set per side.
    # Split quantities, not physical ownership: each item is counted once.
    for child in children:
        child.hardware.extend(
            HardwareItem(h.name, h.quantity // 2, h.notes) for h in assembly.hardware
        )
    assembly.hardware.clear()
