"""Crank-driven gear-pump review; seals/relief valve remain bench prerequisites."""

from efficio.examples.lubricated_engine import (
    lubricated_engine_assembly,
    lubrication_geometry,
)
from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.fits import Process
from efficio.objects.fluids import Point3, TubeNetwork
from efficio.objects.gears.involute import mesh_phase
from efficio.objects.gears.spur import SpurGear
from efficio.objects.powertrain.engine.pump_mount import (
    DrilledSupport,
    PumpMount,
    PumpMountGeometry,
)
from efficio.objects.pumps.external_gear import GearPumpGeometry, gear_pump_assembly
from efficio.objects.pumps.geometry import StrainerGeometry
from efficio.objects.pumps.strainer import StrainerPart

PUMP_ORIGIN = (-40.0, -35.0, 0.0)
FILTER_ORIGIN = (-70.0, 20.0, 16.0)


def pump_geometry() -> GearPumpGeometry:
    return GearPumpGeometry()


def filter_geometry() -> StrainerGeometry:
    return StrainerGeometry(7, 2, 20, 3, 1.5, 0.8, 0.2, 2.7, 8)


def pump_point(p: tuple[float, float, float]) -> tuple[float, float, float]:
    return (p[0] + PUMP_ORIGIN[0], p[2] + PUMP_ORIGIN[1], -p[1])


def external_lines() -> dict[str, TubeNetwork]:
    g = pump_geometry()
    # Positive engine crank angle produces CCW pump rotor viewed from +local Z:
    # +local Y is therefore suction, which maps to the lower world-Z port.
    suction: list[Point3] = [
        pump_point(g.port(1)),
        (-34, -28.9, -20),
        (-85, -28.9, -20),
        (-85, 48, -20),
        (-85, 48, -16),
        (-42, 48, -16),
    ]
    pressure: list[Point3] = [
        pump_point(g.port(-1)),
        (-34, -28.9, 20),
        (-70, -28.9, 20),
        (-70, -28.9, 16),
        FILTER_ORIGIN,
    ]
    delivery: list[Point3] = [(-70, 40, 16), (-70, 48, 16), (-42, 48, 16)]
    # Two separate interfaces reserve an external, rated relief valve. This gap
    # is deliberately NOT called a connected or operational bypass.
    relief_feed: list[Point3] = [(-70, 0, 16), (-86, 0, 16)]
    return_line: list[Point3] = [
        (-86, 12, 16),
        (-94, 12, 16),
        (-94, 48, 16),
        (-94, 48, -16),
        (-85, 48, -16),
    ]
    return {
        "pump_suction_line": TubeNetwork([suction, return_line], 1.5, 1),
        "pump_pressure_line": TubeNetwork([pressure, relief_feed], 1.5, 1),
        "pump_delivery_line": TubeNetwork([delivery], 1.5, 1),
    }


def pump_drive_phase(crank_angle: float) -> float:
    """Unwrapped shaft phase: tooth-equivalent angle wrapping would jump D flats."""
    return mesh_phase((0, 0), 0, 18, (-40, 0), 22) - (18 / 22) * crank_angle


def pumped_engine_assembly(crank_angle: float = 30.0) -> Assembly:
    root = lubricated_engine_assembly(crank_angle)
    oil = root.find("Lubrication")
    phase = pump_drive_phase(crank_angle)
    pump = gear_pump_assembly(pump_geometry(), -phase)
    for p in pump.all_instances():
        p.solid = p.solid.rotate((0, 0, 0), (1, 0, 0), -90).translate(PUMP_ORIGIN)
    oil.add_subassembly(pump)
    drive = oil.add_subassembly(Assembly("Pump drive", (186, 113, 55)))
    for name, teeth, bore, x, spin in [
        ("pump_crank_gear", 18, 8, 0, crank_angle),
        ("pump_drive_gear", 22, 4, -40, phase),
    ]:
        gear = SpurGear(
            2, teeth, Millimeter(5), Millimeter(bore), True, backlash=Millimeter(0.15)
        )
        spec = PartSpec(
            name,
            gear,
            (Process.RESIN_CAST,),
            "finish-machined candidate",
            "D-flat torque interface; axial collars/fasteners and gear guard not yet selected",
        )
        drive.place_axial(spec, name, x, 0, -7.5, True, spin)
    strainer = oil.add_subassembly(Assembly("Serviceable oil strainer", (163, 116, 49)))
    for kind in ("body", "cap", "screen"):
        spec = PartSpec(
            "oil_filter_" + kind,
            StrainerPart(filter_geometry(), kind),
            (Process.RESIN_CAST,),
            "material undecided",
            "0.4 mm holes: coarse strainer, not fine filter media; cap seal/clamp and screen retention unresolved",
        )
        strainer.place_axial(
            spec, spec.name, FILTER_ORIGIN[0], FILTER_ORIGIN[2], FILTER_ORIGIN[1], True
        )
    lines = oil.add_subassembly(Assembly("External oil lines", (204, 150, 43)))
    for name, obj in external_lines().items():
        spec = PartSpec(
            name,
            obj,
            (Process.RESIN_CAST,),
            "formed tube/fittings undecided",
            "Open relief service interfaces require rated valve before pressure operation; no connected relief claim",
        )
        lines.place_world(spec, name, 0, 0, 0)
    # Screen fits within existing pickup bore; no cylinder-wall change.
    pickup = lubrication_geometry().pickup_path()[0]
    screen_g = StrainerGeometry(2, 0.5, 2, 0.4, 0.5, 0.3, 0.25, 0.8, 6)
    spec = PartSpec(
        "pickup_screen",
        StrainerPart(screen_g, "screen"),
        (Process.RESIN_CAST,),
        "fine metal perforated insert candidate",
        "0.5 mm holes; seating/retention unresolved, not a rated mesh",
    )
    lines.place_world(
        spec, spec.name, pickup[0], pickup[1], pickup[2] - screen_g.length / 2
    )
    mount_g = PumpMountGeometry(
        tuple((x - 40, -y) for x, y in pump_geometry().bolt_points),
        ((-18, 40), (18, 40)),
        (-55, -15),
        (-16, 44),
        (-22, 22),
        (36, 44),
        -41,
        3,
        -35,
        0,
        1.65,
        3,
    )
    mount = oil.add_subassembly(Assembly("Pump mounting adapter", (119, 133, 148)))
    spec = PartSpec(
        "pump_mount",
        PumpMount(mount_g),
        (Process.RESIN_CAST,),
        "metal preferred; strength unqualified",
        "Four pump through bolts and two engine through bolts; lengths, nuts, loads and assembly access not qualified",
    )
    mount.place_world(spec, spec.name, 0, 0, 0)
    front = root.instance("resin_front_support")
    replacement = PartSpec(
        "resin_front_support_pump",
        DrilledSupport(
            front.spec.obj, mount_g.engine_holes, mount_g.hole_radius, -1, 9
        ),
        front.spec.processes,
        front.spec.material,
        "Original end support with two 3.3 mm pump mounting holes at X +/-18, Z40",
    )
    front.owner.parts.pop(front.part)
    front.owner.register(replacement)
    front.spec, front.part, front.solid = (
        replacement,
        replacement.name,
        replacement.solid(),
    )
    return root
