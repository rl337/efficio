"""Rear transaxle: twin-cylinder engine, 11.5:1 spur reduction, spur
differential, half-shafts and wheels, laid out from ``DrivetrainLayout``."""

import argparse
import logging
from typing import Dict, List, Optional

from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.drivetrain import (
    CompoundSpurGear,
    DifferentialCarrierHalf,
    DifferentialPlanet,
    DifferentialSun,
    GearboxPlate,
    PlateSide,
    Shaft,
    SpurGear,
    Standoff,
)
from efficio.objects.drivetrain_layout import DrivetrainLayout, Span
from efficio.objects.engine import (
    ConnectingRod,
    CrankWeb,
    CylinderHead,
    EngineBlockHalf,
    Flywheel,
    Piston,
)
from efficio.objects.fits import Process
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.wheels import HexWheelAdapter, PillowBlock, Rim, Tire

PRINT = Process.FDM_PRINT
CNC = Process.CNC_PLATE
ROD = Process.ROD_STOCK

PILLOW_CENTRE_HEIGHT_MM = 15.0


def _module(layout: DrivetrainLayout) -> MetricModule:
    return MetricModule(layout.module)


def _pressure(layout: DrivetrainLayout) -> PressureAngle:
    return PressureAngle(layout.pressure_angle)


def _rod(name: str, diameter: float, span: Span, d_flat: bool, notes: str) -> PartSpec:
    return PartSpec(
        name,
        Shaft(Millimeter(diameter), Millimeter(span.length), d_flat),
        (ROD,),
        f"{diameter:g} mm ground steel rod",
        notes,
    )


def _engine_specs(layout: DrivetrainLayout) -> Dict[str, PartSpec]:
    return {
        "block_upper": PartSpec(
            "engine_block_upper",
            EngineBlockHalf(layout, upper=True),
            (PRINT,),
            "PETG / ASA",
            "Print deck-up; tap M3 holes or use heat-set inserts",
        ),
        "block_lower": PartSpec(
            "engine_block_lower",
            EngineBlockHalf(layout, upper=False),
            (PRINT,),
            "PETG / ASA",
            "Print split-face down",
        ),
        "head": PartSpec(
            "cylinder_head",
            CylinderHead(layout),
            (CNC, PRINT),
            "6061 aluminium plate or PETG",
            f"{layout.head_thickness:g} mm stock",
        ),
        "piston": PartSpec(
            "piston",
            Piston(layout),
            (PRINT,),
            "PETG / nylon",
            "Print crown-up; ream wrist-pin bore",
        ),
        "rod": PartSpec(
            "connecting_rod",
            ConnectingRod(layout),
            (CNC, PRINT),
            "6061 aluminium plate or nylon",
            f"{layout.rod_thickness:g} mm stock",
        ),
        "web": PartSpec(
            "crank_web",
            CrankWeb(layout),
            (CNC, PRINT),
            "6061 aluminium plate or PETG",
            f"{layout.web_thickness:g} mm stock; ream journal/pin holes",
        ),
        "flywheel": PartSpec(
            "flywheel",
            Flywheel(
                Millimeter(layout.flywheel_diameter),
                Millimeter(layout.flywheel_thickness),
                Millimeter(layout.crank_journal_diameter),
                4,
            ),
            (CNC, PRINT),
            "Steel / brass plate or PETG",
            f"{layout.flywheel_thickness:g} mm stock",
        ),
        "wrist_pin": _rod(
            "wrist_pin",
            layout.wrist_pin_diameter,
            Span(0.0, layout.bore - 2.0),
            False,
            "Press into piston",
        ),
        "crankpin": _rod(
            "crankpin",
            layout.crankpin_diameter,
            Span(-layout.web_outer_offset, layout.web_outer_offset),
            False,
            "Press through both webs of a throw",
        ),
        "crank_stub": _rod(
            "crank_output_stub",
            layout.crank_journal_diameter,
            layout.crank_stub,
            True,
            "D-flat full length; drives crank pinion",
        ),
        "flywheel_stub": _rod(
            "crank_flywheel_stub",
            layout.crank_journal_diameter,
            layout.flywheel_stub,
            True,
            "D-flat full length; carries flywheel",
        ),
    }


def add_engine(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    specs = _engine_specs(layout)
    cx, cz = layout.crank_centre
    y0 = layout.engine_block.start
    pose = layout.engine_pose(crank_angle)

    assembly.place_world(specs["block_upper"], "engine_block_upper", cx, y0, cz)
    assembly.place_world(specs["block_lower"], "engine_block_lower", cx, y0, cz)
    assembly.place_world(
        specs["head"], "cylinder_head", cx, y0, cz + layout.deck_height
    )

    assembly.place_axial(
        specs["crank_stub"],
        "crank_output_stub",
        cx,
        cz,
        layout.crank_stub.start,
        True,
        crank_angle,
    )
    assembly.place_axial(
        specs["flywheel_stub"],
        "crank_flywheel_stub",
        cx,
        cz,
        layout.flywheel_stub.start,
        True,
        crank_angle,
    )
    assembly.place_axial(
        specs["flywheel"], "flywheel", cx, cz, layout.flywheel.start, True, crank_angle
    )

    for index, journal in enumerate(layout.centre_journals()):
        spec = assembly.register(
            _rod(
                "crank_centre_journal",
                layout.crank_journal_diameter,
                journal,
                False,
                "Press between adjacent throws",
            )
        )
        assembly.place_axial(
            spec, f"crank_centre_journal_{index}", cx, cz, journal.start, True
        )

    for i in range(layout.cylinders):
        y = layout.cylinder_y(i)
        throw = crank_angle + 360.0 * i / layout.cylinders
        px, pz = pose.crankpin_centres[i]
        wrist_z = pose.wrist_pin_heights[i]
        assembly.place_axial(
            specs["web"],
            f"crank_web_{i}_a",
            cx,
            cz,
            y - layout.web_outer_offset,
            True,
            throw,
        )
        assembly.place_axial(
            specs["web"],
            f"crank_web_{i}_b",
            cx,
            cz,
            y + layout.web_inner_offset,
            True,
            throw,
        )
        assembly.place_axial(
            specs["crankpin"],
            f"crankpin_{i}",
            px,
            pz,
            y - layout.web_outer_offset,
            True,
        )
        assembly.place_axial(
            specs["rod"],
            f"connecting_rod_{i}",
            px,
            pz,
            y,
            False,
            pose.rod_angles[i] - 90.0,
        )
        assembly.place_world(specs["piston"], f"piston_{i}", cx, y, wrist_z)
        pin_length = layout.bore - 2.0
        assembly.place_axial(
            specs["wrist_pin"], f"wrist_pin_{i}", cx, wrist_z, y - pin_length / 2, True
        )

    n = layout.cylinders
    assembly.add_hardware(
        f"{layout.crank_bearing.designation} ball bearing",
        2,
        "Crank mains in block end walls",
    )
    assembly.add_hardware("M3 x 20 socket cap screw", 4 * n, "Cylinder head")
    assembly.add_hardware("M3 x 30 socket cap screw", 4, "Block split bolts")
    assembly.add_hardware(
        "M3 x 16 socket cap screw", 4, "Engine to right gearbox plate"
    )


def add_gearbox(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    module = _module(layout)
    pressure = _pressure(layout)
    phases = layout.gear_phases(crank_angle)
    ax, az = layout.axle_centre
    ix, iz = layout.idler_centre
    cx, cz = layout.crank_centre

    plate_left = PartSpec(
        "gearbox_plate_left",
        GearboxPlate(layout, PlateSide.LEFT),
        (CNC, PRINT),
        "6061 aluminium plate or PETG",
        f"{layout.plate_thickness:g} mm stock; bearing seats pocketed from inner face",
    )
    plate_right = PartSpec(
        "gearbox_plate_right",
        GearboxPlate(layout, PlateSide.RIGHT),
        (CNC, PRINT),
        "6061 aluminium plate or PETG",
        f"{layout.plate_thickness:g} mm stock; engine flange face",
    )
    assembly.place_axial(
        plate_left, "gearbox_plate_left", 0.0, 0.0, layout.plate_left.end, False
    )
    assembly.place_axial(
        plate_right, "gearbox_plate_right", 0.0, 0.0, layout.plate_right.start, True
    )

    gap = Span(layout.plate_left.end, layout.plate_right.start)
    standoff = PartSpec(
        "gearbox_standoff",
        Standoff(Millimeter(gap.length), Millimeter(2 * layout.standoff_radius)),
        (PRINT,),
        "PETG",
        "Clamp with M3 threaded rod",
    )
    for i, (sx, sz) in enumerate(layout.standoff_centres()):
        assembly.place_axial(standoff, f"gearbox_standoff_{i}", sx, sz, gap.start, True)

    pinion = PartSpec(
        "crank_pinion",
        SpurGear(
            module,
            layout.crank_pinion_teeth,
            Millimeter(layout.stage_gear_width),
            Millimeter(layout.crank_journal_diameter),
            True,
            pressure,
        ),
        (PRINT, CNC),
        "Nylon / acetal",
        f"{layout.crank_pinion_teeth}T m{layout.module:g} {layout.pressure_angle:g} deg",
    )
    assembly.place_axial(
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
        ),
        (PRINT,),
        "Nylon / PETG",
        f"{layout.idler_pinion_teeth}T + {layout.idler_gear_teeth}T; print large gear down",
    )
    assembly.place_axial(
        idler,
        "idler_compound_gear",
        ix,
        iz,
        layout.idler_pinion_span.start,
        True,
        phases["idler"],
    )
    idler_shaft = _rod(
        "idler_shaft",
        layout.idler_shaft_diameter,
        layout.idler_shaft,
        True,
        "D-flat full length",
    )
    assembly.place_axial(
        idler_shaft,
        "idler_shaft",
        ix,
        iz,
        layout.idler_shaft.start,
        True,
        phases["idler"],
    )

    # Differential.
    carrier = phases["carrier"]
    left_half = PartSpec(
        "diff_carrier_left",
        DifferentialCarrierHalf(layout, Millimeter(layout.carrier_left_hub.length)),
        (PRINT,),
        "Nylon / PETG",
        f"{layout.ring_teeth}T ring gear half; print split-face down",
    )
    right_half = PartSpec(
        "diff_carrier_right",
        DifferentialCarrierHalf(layout, Millimeter(layout.carrier_right_hub.length)),
        (PRINT,),
        "Nylon / PETG",
        f"{layout.ring_teeth}T ring gear half; print split-face down",
    )
    assembly.place_axial(
        left_half, "diff_carrier_left", ax, az, layout.drum.centre, False, carrier
    )
    assembly.place_axial(
        right_half, "diff_carrier_right", ax, az, layout.drum.centre, True, carrier
    )

    sun = PartSpec(
        "diff_sun_gear",
        DifferentialSun(layout),
        (PRINT,),
        "Nylon / acetal",
        f"{layout.sun_teeth}T, D-bore for {layout.axle_diameter:g} mm axle",
    )
    sun_a = phases["sun_a"]
    poses = layout.planet_poses(carrier, sun_a)
    sun_b = layout.sun_b_phase(poses)
    assembly.place_axial(sun, "diff_sun_left", ax, az, layout.sun_a.start, True, sun_a)
    assembly.place_axial(sun, "diff_sun_right", ax, az, layout.sun_b.end, False, sun_b)

    planet = PartSpec(
        "diff_planet_gear",
        DifferentialPlanet(layout),
        (PRINT, CNC),
        "Nylon / acetal",
        f"{layout.planet_teeth}T, runs on M3 bolt",
    )
    pin = _rod(
        "diff_planet_pin", 3.0, layout.drum, False, "Shank of the M3 planet bolt"
    )
    for pose in poses:
        px, pz = pose.centre
        assembly.place_axial(
            planet,
            f"diff_planet_{pose.name}",
            px,
            pz,
            pose.span.start,
            True,
            pose.phase,
        )
        assembly.place_axial(
            pin, f"diff_planet_pin_{pose.name}", px, pz, layout.drum.start, True
        )

    planets = len(poses)
    assembly.add_hardware(
        f"{layout.carrier_bearing.designation} ball bearing",
        2,
        "Carrier hubs in gearbox plates",
    )
    assembly.add_hardware(
        f"{layout.idler_bearing.designation} ball bearing",
        2,
        "Idler shaft in gearbox plates",
    )
    assembly.add_hardware(
        f"{layout.crank_bearing.designation} ball bearing",
        1,
        "Crank stub outboard support, left plate",
    )
    assembly.add_hardware(
        "M3 x 35 socket cap screw + nut", planets, "Planet pins; clamp carrier halves"
    )
    assembly.add_hardware(
        f"M3 threaded rod x {gap.length + 2 * layout.plate_thickness + 6:g} mm + 2 nuts",
        len(layout.standoff_centres()),
        "Gearbox standoff tie rods",
    )


def add_axles_and_wheels(
    assembly: Assembly, layout: DrivetrainLayout, crank_angle: float
) -> None:
    ax, az = layout.axle_centre
    phases = layout.gear_phases(crank_angle)
    sun_a = phases["sun_a"]
    sun_b = layout.sun_b_phase(layout.planet_poses(phases["carrier"], sun_a))

    left = _rod(
        "half_shaft_left",
        layout.axle_diameter,
        layout.left_half_shaft,
        True,
        "Drill & tap M3 in wheel end",
    )
    right = _rod(
        "half_shaft_right",
        layout.axle_diameter,
        layout.right_half_shaft,
        True,
        "Drill & tap M3 in wheel end",
    )
    assembly.place_axial(
        left, "half_shaft_left", ax, az, layout.left_half_shaft.start, True, sun_a
    )
    assembly.place_axial(
        right, "half_shaft_right", ax, az, layout.right_half_shaft.start, True, sun_b
    )

    pillow = PartSpec(
        "axle_pillow_block",
        PillowBlock(
            Millimeter(layout.axle_diameter),
            Millimeter(layout.axle_bearing.outer_diameter),
            Millimeter(layout.axle_bearing.width),
            Millimeter(PILLOW_CENTRE_HEIGHT_MM),
            Millimeter(layout.pillow_block_thickness),
        ),
        (PRINT,),
        "PETG",
        "Bolts to your chassis rail",
    )
    assembly.place_axial(
        pillow, "axle_pillow_left", ax, az, layout.left_pillow_block.end, False
    )
    assembly.place_axial(
        pillow, "axle_pillow_right", ax, az, layout.right_pillow_block.end, False
    )

    adapter = PartSpec(
        "wheel_hex_adapter",
        HexWheelAdapter(
            Millimeter(layout.hex_across_flats),
            Millimeter(layout.hex_adapter_length),
            Millimeter(layout.axle_diameter),
        ),
        (PRINT, CNC),
        "Nylon / aluminium",
        f"{layout.hex_across_flats:g} mm hex",
    )
    rim = PartSpec(
        "wheel_rim",
        Rim(
            Millimeter(layout.rim_diameter),
            Millimeter(layout.wheel_width),
            Millimeter(layout.hex_across_flats),
            Millimeter(layout.hex_adapter_length),
            5,
        ),
        (PRINT,),
        "PETG",
        "Print inboard face down",
    )
    tire_width = layout.wheel_width - 4.0
    tire = PartSpec(
        "wheel_tire",
        Tire(
            Millimeter(layout.wheel_diameter),
            Millimeter(layout.rim_diameter),
            Millimeter(tire_width),
            24,
        ),
        (PRINT,),
        "TPU 95A",
        "Stretch over rim lip",
    )
    lw, rw = layout.left_wheel, layout.right_wheel
    assembly.place_axial(adapter, "wheel_hex_left", ax, az, lw.end, False, sun_a)
    assembly.place_axial(adapter, "wheel_hex_right", ax, az, rw.start, True, sun_b)
    assembly.place_axial(rim, "wheel_rim_left", ax, az, lw.end, False, sun_a)
    assembly.place_axial(rim, "wheel_rim_right", ax, az, rw.start, True, sun_b)
    assembly.place_axial(tire, "wheel_tire_left", ax, az, lw.end - 2.0, False)
    assembly.place_axial(tire, "wheel_tire_right", ax, az, rw.start + 2.0, True)

    assembly.add_hardware(
        f"{layout.axle_bearing.designation} ball bearing", 2, "Axle pillow blocks"
    )
    assembly.add_hardware(
        "M3 x 10 socket cap screw + washer", 2, "Wheel retention into axle end"
    )
    assembly.add_hardware("M3 x 12 socket cap screw", 4, "Pillow blocks to chassis")


def engine_assembly(
    layout: Optional[DrivetrainLayout] = None, crank_angle: float = 0.0
) -> Assembly:
    layout = layout or DrivetrainLayout()
    assembly = Assembly("Twin-cylinder model engine")
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
    add_axles_and_wheels(assembly, layout, crank_angle)
    return assembly


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
