"""Rear transaxle: inline engine, two-stage spur reduction, spur differential,
half-shafts and wheels, assembled from a :class:`DrivetrainLayout`.

Every part is a parameterised powertrain object; this module only decides
which ones the layout needs, where they go and how they are made.
"""

import argparse
import logging
from typing import Dict, List, Optional

from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.base import EfficioObject
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.powertrain.axles import HexWheelAdapter, PillowBlock
from efficio.objects.powertrain.differential import (
    SpurDifferentialCarrierHalf,
    planet_gear,
    sun_gear,
)
from efficio.objects.powertrain.engine import (
    ConnectingRod,
    CrankWeb,
    CylinderHead,
    EngineBlockHalf,
    Flywheel,
    Piston,
)
from efficio.objects.powertrain.fits import Process
from efficio.objects.powertrain.gearbox import BearingPlate
from efficio.objects.powertrain.gears import CompoundSpurGear, SpurGear
from efficio.objects.powertrain.layout import AxleStock, DrivetrainLayout, PlateSide
from efficio.objects.powertrain.planar import Span
from efficio.objects.powertrain.shafts import Shaft, Standoff
from efficio.objects.powertrain.wheels import Rim, Tire
from efficio.objects.shapes import Shape

PRINT = Process.FDM_PRINT
CNC = Process.CNC_PLATE
ROD = Process.ROD_STOCK
DOWEL = Process.DOWEL_STOCK
BOUGHT = Process.PURCHASED

PLATE_MATERIAL = "6061 aluminium plate or PETG"
GEAR_MATERIAL = "Nylon / acetal"


def rod_stock(
    name: str, diameter: float, span: Span, d_flat: bool, notes: str
) -> PartSpec:
    return PartSpec(
        name,
        Shaft(Millimeter(diameter), Millimeter(span.length), d_flat),
        (ROD,),
        f"{diameter:g} mm ground steel rod",
        notes,
    )


def _module(layout: DrivetrainLayout) -> MetricModule:
    return MetricModule(layout.module)


def _pressure(layout: DrivetrainLayout) -> PressureAngle:
    return PressureAngle(layout.pressure_angle)


# ---------------------------------------------------------------------- engine
def add_engine(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    engine = layout.engine
    cx, cz = layout.crank_centre
    y0 = layout.engine_origin_y
    pose = engine.pose(crank_angle)
    journal = engine.crank_journal_diameter

    upper = PartSpec(
        "engine_block_upper",
        EngineBlockHalf(engine, upper=True),
        (PRINT,),
        "PETG / ASA",
        "Print deck-up; tap M3 holes or use heat-set inserts",
    )
    lower = PartSpec(
        "engine_block_lower",
        EngineBlockHalf(engine, upper=False),
        (PRINT,),
        "PETG / ASA",
        "Print split-face down",
    )
    head = PartSpec(
        "cylinder_head",
        CylinderHead(engine),
        (CNC, PRINT),
        PLATE_MATERIAL,
        f"{engine.head_thickness:g} mm stock",
    )
    assembly.place_world(upper, "engine_block_upper", cx, y0, cz)
    assembly.place_world(lower, "engine_block_lower", cx, y0, cz)
    assembly.place_world(head, "cylinder_head", cx, y0, cz + engine.deck_height)

    web = PartSpec(
        "crank_web",
        CrankWeb.from_engine(engine),
        (CNC, PRINT),
        PLATE_MATERIAL,
        f"{engine.web_thickness:g} mm stock; ream journal/pin holes",
    )
    rod = PartSpec(
        "connecting_rod",
        ConnectingRod.from_engine(engine),
        (CNC, PRINT),
        "6061 aluminium plate or nylon",
        f"{engine.rod_thickness:g} mm stock",
    )
    piston = PartSpec(
        "piston",
        Piston.from_engine(engine),
        (PRINT,),
        "PETG / nylon",
        "Print crown-up; ream wrist-pin bore",
    )
    crankpin = rod_stock(
        "crankpin",
        engine.crankpin_diameter,
        Span(-engine.web_outer_offset, engine.web_outer_offset),
        False,
        "Press through both webs of a throw",
    )
    wrist_pin = rod_stock(
        "wrist_pin",
        engine.wrist_pin_diameter,
        Span(0.0, engine.wrist_pin_length),
        False,
        "Press into piston",
    )
    output_stub = rod_stock(
        "crank_output_stub",
        journal,
        layout.crank_stub,
        True,
        "D-flat full length; drives crank pinion",
    )
    flywheel_stub = rod_stock(
        "crank_flywheel_stub",
        journal,
        layout.flywheel_stub,
        True,
        "D-flat full length; carries flywheel",
    )
    flywheel = PartSpec(
        "flywheel",
        Flywheel(
            Millimeter(layout.flywheel_diameter),
            Millimeter(layout.flywheel_thickness),
            Millimeter(journal),
            layout.flywheel_holes,
        ),
        (CNC, PRINT),
        "Steel / brass plate or PETG",
        f"{layout.flywheel_thickness:g} mm stock",
    )

    place = assembly.place_axial
    place(
        output_stub,
        "crank_output_stub",
        cx,
        cz,
        layout.crank_stub.start,
        True,
        crank_angle,
    )
    place(
        flywheel_stub,
        "crank_flywheel_stub",
        cx,
        cz,
        layout.flywheel_stub.start,
        True,
        crank_angle,
    )
    place(flywheel, "flywheel", cx, cz, layout.flywheel.start, True, crank_angle)
    for index, span in enumerate(layout.centre_journals()):
        centre_journal = rod_stock(
            "crank_centre_journal",
            journal,
            span,
            False,
            "Press between adjacent throws",
        )
        place(centre_journal, f"crank_centre_journal_{index}", cx, cz, span.start, True)

    for i in range(engine.cylinders):
        y = layout.cylinder_y(i)
        throw = pose.throw_angles[i]
        px, pz = pose.crankpin_centres[i]
        wrist_z = cz + pose.wrist_pin_heights[i]
        place(web, f"crank_web_{i}_a", cx, cz, y - engine.web_outer_offset, True, throw)
        place(web, f"crank_web_{i}_b", cx, cz, y + engine.web_inner_offset, True, throw)
        place(
            crankpin,
            f"crankpin_{i}",
            cx + px,
            cz + pz,
            y - engine.web_outer_offset,
            True,
        )
        place(
            rod,
            f"connecting_rod_{i}",
            cx + px,
            cz + pz,
            y,
            False,
            pose.rod_angles[i] - 90.0,
        )
        assembly.place_world(piston, f"piston_{i}", cx, y, wrist_z)
        place(
            wrist_pin,
            f"wrist_pin_{i}",
            cx,
            wrist_z,
            y - engine.wrist_pin_length / 2,
            True,
        )

    assembly.add_hardware(
        f"{engine.main_bearing.designation} ball bearing",
        2,
        "Crank mains in block end walls",
    )
    assembly.add_hardware(
        "M3 x 20 socket cap screw", len(engine.head_bolt_positions()), "Cylinder head"
    )
    assembly.add_hardware(
        "M3 x 30 socket cap screw",
        len(engine.split_bolt_positions()),
        "Block split bolts",
    )
    assembly.add_hardware(
        "M3 x 16 socket cap screw",
        len(engine.flange_bolt_offsets()),
        "Engine to right gearbox plate",
    )


# --------------------------------------------------------------------- gearbox
def add_gearbox(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    module = _module(layout)
    pressure = _pressure(layout)
    backlash = Millimeter(layout.backlash)
    phases = layout.gear_phases(crank_angle)
    ix, iz = layout.idler_centre
    cx, cz = layout.crank_centre
    place = assembly.place_axial

    for side, span, toward_positive in (
        (PlateSide.LEFT, layout.plate_left, False),
        (PlateSide.RIGHT, layout.plate_right, True),
    ):
        seats, holes = layout.plate_features(side)
        plate = PartSpec(
            f"gearbox_plate_{side.value}",
            BearingPlate(Millimeter(layout.plate_thickness), seats, holes),
            (CNC, PRINT),
            PLATE_MATERIAL,
            f"{layout.plate_thickness:g} mm stock; bearing seats pocketed from inner face",
        )
        y = span.start if toward_positive else span.end
        place(plate, f"gearbox_plate_{side.value}", 0.0, 0.0, y, toward_positive)

    gap = layout.plate_gap
    standoff = PartSpec(
        "gearbox_standoff",
        Standoff(Millimeter(gap.length), Millimeter(2 * layout.standoff_radius)),
        (PRINT,),
        "PETG",
        "Clamp with M3 threaded rod",
    )
    for i, (sx, sz) in enumerate(layout.standoff_centres()):
        place(standoff, f"gearbox_standoff_{i}", sx, sz, gap.start, True)

    pinion = PartSpec(
        "crank_pinion",
        SpurGear(
            module,
            layout.crank_pinion_teeth,
            Millimeter(layout.stage_gear_width),
            Millimeter(layout.engine.crank_journal_diameter),
            True,
            pressure,
            backlash=backlash,
        ),
        (PRINT, CNC),
        GEAR_MATERIAL,
        f"{layout.crank_pinion_teeth}T m{layout.module:g} {layout.pressure_angle:g} deg",
    )
    place(
        pinion,
        "crank_pinion",
        cx,
        cz,
        layout.stage_plane.start,
        True,
        phases["crank_pinion"],
    )

    idler = PartSpec(
        "idler_compound_gear",
        CompoundSpurGear(
            module,
            layout.idler_pinion_teeth,
            Millimeter(layout.idler_pinion_span.length),
            layout.idler_gear_teeth,
            Millimeter(layout.stage_gear_width),
            Millimeter(layout.idler_shaft_diameter),
            pressure,
            backlash,
        ),
        (PRINT,),
        "Nylon / PETG",
        f"{layout.idler_pinion_teeth}T + {layout.idler_gear_teeth}T; print large gear down",
    )
    place(
        idler,
        "idler_compound_gear",
        ix,
        iz,
        layout.idler_pinion_span.start,
        True,
        phases["idler"],
    )
    idler_shaft = rod_stock(
        "idler_shaft",
        layout.idler_shaft_diameter,
        layout.idler_shaft,
        True,
        "D-flat full length",
    )
    place(
        idler_shaft,
        "idler_shaft",
        ix,
        iz,
        layout.idler_shaft.start,
        True,
        phases["idler"],
    )

    assembly.add_hardware(
        f"{layout.carrier_bearing.spec.designation} ball bearing",
        2,
        "Carrier hubs in gearbox plates",
    )
    assembly.add_hardware(
        f"{layout.idler_bearing.spec.designation} ball bearing",
        2,
        "Idler shaft in gearbox plates",
    )
    assembly.add_hardware(
        f"{layout.crank_support_bearing.spec.designation} ball bearing",
        1,
        "Crank stub outboard support, left plate",
    )
    assembly.add_hardware(
        f"M3 threaded rod x {gap.length + 2 * layout.plate_thickness + 6:g} mm + 2 nuts",
        len(layout.standoff_centres()),
        "Gearbox standoff tie rods",
    )


# ---------------------------------------------------------------- differential
def add_differential(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    diff = layout.differential
    ax, az = layout.axle_centre
    phases = layout.gear_phases(crank_angle)
    carrier = phases["carrier"]
    sun_a = phases["sun_a"]
    poses = layout.planet_poses(carrier, sun_a)
    sun_b = layout.sun_b_phase(poses)
    place = assembly.place_axial

    for name, hub, toward_positive in (
        ("diff_carrier_left", layout.carrier_left_hub, False),
        ("diff_carrier_right", layout.carrier_right_hub, True),
    ):
        half = PartSpec(
            name,
            SpurDifferentialCarrierHalf(diff, Millimeter(hub.length)),
            (PRINT,),
            "Nylon / PETG",
            f"{diff.ring_teeth}T ring gear half; print split-face down",
        )
        place(half, name, ax, az, layout.drum.centre, toward_positive, carrier)

    sun = PartSpec(
        "diff_sun_gear",
        sun_gear(diff),
        (PRINT,),
        GEAR_MATERIAL,
        f"{diff.sun_teeth}T, D-bore for {diff.axle_diameter:g} mm axle",
    )
    place(sun, "diff_sun_left", ax, az, layout.sun_a.start, True, sun_a)
    place(sun, "diff_sun_right", ax, az, layout.sun_b.end, False, sun_b)

    planet = PartSpec(
        "diff_planet_gear",
        planet_gear(diff),
        (PRINT, CNC),
        GEAR_MATERIAL,
        f"{diff.planet_teeth}T, runs on an M3 bolt",
    )
    # The planet pins are the shanks of bought M3 bolts: modelled for the
    # interference check, listed once in the BOM as hardware.
    bolt = PartSpec(
        f"M3 x {layout.drum.length:g} socket cap screw (planet pin)",
        Shaft(
            Millimeter(diff.planet_pin_diameter), Millimeter(layout.drum.length), False
        ),
        (BOUGHT,),
        "Steel",
        "Clamps the carrier halves; nut in opposite pocket",
    )
    for pose in poses:
        px, pz = pose.centre
        place(
            planet,
            f"diff_planet_{pose.name}",
            px,
            pz,
            pose.span.start,
            True,
            pose.phase,
        )
        place(bolt, f"diff_planet_pin_{pose.name}", px, pz, layout.drum.start, True)
    assembly.add_hardware("M3 hex nut", len(poses), "Planet bolts")


# ------------------------------------------------------------ axles and wheels
def _half_shaft(layout: DrivetrainLayout, name: str, span: Span) -> PartSpec:
    """Steel D-flat rod, or a cross-drilled hardwood dowel."""
    if not layout.dowel_axles:
        return rod_stock(
            name, layout.axle_diameter, span, True, "Drill & tap M3 in wheel end"
        )
    side = "left" if name.endswith("left") else "right"
    pins = layout.axle_cross_pins()
    holes = sorted(
        abs(pins[f"{where}_{side}"] - span.start) for where in ("sun", "wheel")
    )
    dowel = layout.axle_dowel.spec
    return PartSpec(
        name,
        Shaft(
            Millimeter(dowel.diameter),
            Millimeter(span.length),
            False,
            holes,
            Millimeter(layout.cross_pin_diameter),
        ),
        (DOWEL,),
        dowel.description(),
        f"Cut {span.length:.0f} mm; drill {layout.cross_pin_diameter:g} mm cross holes "
        f"at {holes[0]:.1f} and {holes[1]:.1f} mm from the inboard end",
    )


def add_cross_pins(
    assembly: Assembly, layout: DrivetrainLayout, phases: Dict[str, float]
) -> None:
    """Pins that drive the dowel axles through the sun gears and wheel hubs."""
    pins = layout.axle_cross_pins()
    if not pins:
        return
    ax, az = layout.axle_centre
    pin = PartSpec(
        "axle_cross_pin",
        Shaft(
            Millimeter(layout.cross_pin_diameter),
            Millimeter(layout.cross_pin_length),
            False,
        ),
        (ROD,),
        f"{layout.cross_pin_diameter:g} mm steel rod (or a cut nail)",
        f"Cut {layout.cross_pin_length:g} mm; tap through the dowel into the slot",
    )
    for where, y in pins.items():
        side = where.split("_")[1]
        assembly.place_radial(pin, f"axle_cross_pin_{where}", ax, y, az, phases[side])


def add_axles_and_wheels(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    ax, az = layout.axle_centre
    phases = layout.gear_phases(crank_angle)
    sun_a = phases["sun_a"]
    sun_b = layout.sun_b_phase(layout.planet_poses(phases["carrier"], sun_a))
    spin = {"left": sun_a, "right": sun_b}
    axle = layout.axle_diameter
    place = assembly.place_axial

    left = _half_shaft(layout, "half_shaft_left", layout.left_half_shaft)
    right = _half_shaft(layout, "half_shaft_right", layout.right_half_shaft)
    place(left, "half_shaft_left", ax, az, layout.left_half_shaft.start, True, sun_a)
    place(right, "half_shaft_right", ax, az, layout.right_half_shaft.start, True, sun_b)
    add_cross_pins(assembly, layout, spin)

    pillow = PartSpec(
        "axle_pillow_block",
        PillowBlock(
            Millimeter(axle),
            layout.axle_bearing,
            Millimeter(layout.pillow_centre_height),
            Millimeter(layout.pillow_block_thickness),
        ),
        (PRINT,),
        "PETG",
        f"{layout.axle_bearing.spec.designation} bearing; bolts to your chassis rail",
    )
    place(pillow, "axle_pillow_left", ax, az, layout.left_pillow_block.end, False)
    place(pillow, "axle_pillow_right", ax, az, layout.right_pillow_block.end, False)

    pin_diameter = layout.cross_pin_diameter if layout.dowel_axles else 0.0
    adapter = PartSpec(
        "wheel_hex_adapter",
        HexWheelAdapter(
            Millimeter(layout.hex_across_flats),
            Millimeter(layout.hex_adapter_length),
            Millimeter(axle),
            Millimeter(pin_diameter),
            Millimeter(layout.cross_pin_length if pin_diameter else 0.0),
        ),
        (PRINT, CNC),
        "Nylon / aluminium",
        f"{layout.hex_across_flats:g} mm hex"
        + ("; cross-pin slot faces the wheel" if pin_diameter else ""),
    )
    rim_part = Rim(
        Millimeter(layout.rim_diameter),
        Millimeter(layout.wheel_width),
        Millimeter(layout.hex_across_flats),
        Millimeter(layout.hex_adapter_length),
        layout.rim_spokes,
        Millimeter(layout.rim_spoke_thickness),
        Millimeter(layout.rim_axle_bore),
    )
    rim = PartSpec("wheel_rim", rim_part, (PRINT,), "PETG", "Print inboard face down")
    tire = PartSpec(
        "wheel_tire",
        Tire(
            Millimeter(layout.wheel_diameter),
            Millimeter(layout.rim_diameter),
            Millimeter(rim_part.tire_width()),
            layout.tire_tread_blocks,
        ),
        (PRINT,),
        "TPU 95A",
        "Stretch over rim lip",
    )
    lip = (layout.wheel_width - rim_part.tire_width()) / 2
    lw, rw = layout.left_wheel, layout.right_wheel
    place(adapter, "wheel_hex_left", ax, az, lw.end, False, sun_a)
    place(adapter, "wheel_hex_right", ax, az, rw.start, True, sun_b)
    place(rim, "wheel_rim_left", ax, az, lw.end, False, sun_a)
    place(rim, "wheel_rim_right", ax, az, rw.start, True, sun_b)
    place(tire, "wheel_tire_left", ax, az, lw.end - lip, False)
    place(tire, "wheel_tire_right", ax, az, rw.start + lip, True)

    assembly.add_hardware(
        f"{layout.axle_bearing.spec.designation} ball bearing", 2, "Axle pillow blocks"
    )
    if layout.dowel_axles:
        assembly.add_hardware(
            "#4 x 1/2 in wood screw + washer", 2, "Wheel retention into dowel end grain"
        )
    else:
        assembly.add_hardware(
            "M3 x 10 socket cap screw + washer", 2, "Wheel retention into axle end"
        )
    assembly.add_hardware("M3 x 12 socket cap screw", 4, "Pillow blocks to chassis")


# -------------------------------------------------------------------- builders
def engine_assembly(
    layout: Optional[DrivetrainLayout] = None, crank_angle: float = 0.0
) -> Assembly:
    layout = layout or DrivetrainLayout()
    assembly = Assembly(f"{layout.engine.cylinders}-cylinder model engine")
    add_engine(assembly, layout, crank_angle)
    return assembly


def rear_transaxle(
    layout: Optional[DrivetrainLayout] = None, crank_angle: float = 0.0
) -> Assembly:
    layout = layout or DrivetrainLayout()
    problems = layout.problems()
    if problems:
        raise ValueError("Invalid drivetrain layout: " + "; ".join(problems))
    assembly = Assembly("Rear transaxle drivetrain")
    add_engine(assembly, layout, crank_angle)
    add_gearbox(assembly, layout, crank_angle)
    add_differential(assembly, layout, crank_angle)
    add_axles_and_wheels(assembly, layout, crank_angle)
    return assembly


class RearTransaxle(EfficioObject):
    """Every drivetrain part placed in its assembled position, as one object.

    Exposed to the command line, e.g.::

        python -m efficio --object RearTransaxle \\
            --params crank_angle=0 --params cylinders=2 \\
            --params axle_stock=WOOD_DOWEL --png rear_transaxle.png
    """

    def __init__(
        self,
        crank_angle: float,
        cylinders: int = 2,
        axle_stock: AxleStock = AxleStock.STEEL_D_FLAT,
    ):
        self.crank_angle = crank_angle
        self.cylinders = cylinders
        self.axle_stock = axle_stock

    def layout(self) -> DrivetrainLayout:
        if self.axle_stock is AxleStock.WOOD_DOWEL:
            layout = DrivetrainLayout.with_dowel_axles()
        else:
            layout = DrivetrainLayout()
        layout.engine.cylinders = self.cylinders
        return layout

    def assembly(self) -> Assembly:
        return rear_transaxle(self.layout(), crank_angle=self.crank_angle)

    def shape(self) -> Optional[Shape]:
        return self.assembly().shape()


def export_kit(directory: str, crank_angle: float = 0.0) -> List[str]:
    """Build the default transaxle, verify it, and write the fabrication kit."""
    assembly = rear_transaxle(crank_angle=crank_angle)
    collisions = assembly.interferences()
    if collisions:
        raise ValueError(f"Drivetrain parts interfere: {collisions}")
    return assembly.export(directory)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Export the drivetrain kit")
    parser.add_argument("directory", help="Output directory for STL/DXF/BOM")
    parser.add_argument("--crank-angle", type=float, default=0.0)
    args = parser.parse_args()
    for path in export_kit(args.directory, args.crank_angle):
        logging.info("wrote %s", path)
