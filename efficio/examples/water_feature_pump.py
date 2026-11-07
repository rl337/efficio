"""Independent water-feature wet-end experiment; no engine dependency."""

import math
from dataclasses import replace
from typing import Optional

from efficio.objects.assembly import Assembly, HardwareItem, PartSpec
from efficio.objects.connectors import CommonHoseSize, HoseBarbDimensions, HoseSize
from efficio.objects.fits import Process
from efficio.objects.pumps.blind_support import BlindSupportPart
from efficio.objects.pumps.external_gear import GearPumpGeometry, PumpPart
from efficio.objects.pumps.geometry import BlindSupportDimensions
from efficio.objects.walls import MaterialWallProfile, WallPolicy


def water_pump_dimensions(
    profile: Optional[MaterialWallProfile] = None,
    hose_size: Optional[CommonHoseSize] = None,
) -> BlindSupportDimensions:
    policy = (profile or resin_water_profile()).finished_policy()
    if policy.process != Process.RESIN_CAST:
        raise ValueError(
            "this wet-end builder has only a provisional resin process route"
        )
    minimum = policy.minimum_mm
    # Provisional machining dimensions, not an as-cast tolerance promise.
    g = GearPumpGeometry(
        module=1.25,
        teeth=16,
        width=max(8.0, 2 * (minimum + 2 - 0.08)),
        shaft_diameter=6,
        tip_clearance=0.08,
        face_clearance=0.08,
        journal_clearance=0.04,
        wall=max(10.0, 2 * (minimum + 1.65)),
        base=6 + max(2.0, minimum),
        cover=6 + max(2.0, minimum),
        port_radius=2,
        port_drop=0.3,
        seal_pocket_radius=4,
        collar_radius=5,
        shaft_extension=18,
        rotor_pin_diameter=1.5,
        rotor_pin_length=7.5,
    )
    if hose_size is not None:
        # A larger stem needs a lower centerline to clear the removable cover.
        required_drop = max(
            g.port_drop,
            hose_size.value.id_mm / 2 - g.width / 2 - g.face_clearance + 0.15,
        )
        if required_drop >= g.width / 2 + g.face_clearance - g.port_radius:
            raise ValueError(
                "hose size requires a taller chamber or a different port layout"
            )
        g = replace(g, port_drop=required_drop)
    dimensions = BlindSupportDimensions(
        g,
        back_web=max(2.0, minimum),
        front_web=max(2.0, minimum),
        end_gap=0.03,
        seal_radius=6,
        seal_depth=4,
        gasket_width=1.5,
        gasket_inset=0.7,
        gasket_depth=0.3,
        shaft_radius=2.99,
        exterior_offset=max(
            7.5, math.hypot(g.radius + 0.7 + 1.5 + minimum, g.centres / 2) - g.radius
        ),
        boss_radius=g.bolt_radius + max(3.0, minimum + 0.6),
        bevel=0.6,
    )

    policy.require(dimensions.wall_measurements())
    return dimensions


def water_wall_policy() -> WallPolicy:
    return WallPolicy(
        material="water-compatible casting resin: grade and cure unselected",
        process=Process.RESIN_CAST,
        environment="room-temperature water; supervised low-head experiment",
        minimum_mm=2.0,
        basis="Provisional geometry budget preserving existing 2 mm blind floors; not a strength-derived minimum. Coupon, clamp and hydrostatic validation required.",
        required_features=(
            "offset_side_wall",
            "beveled_offset_bound",
            "bolt_boss_ligament",
            "bolt_to_chamber",
            "rear_blind_floor",
            "idler_cover_floor",
            "seal_seat_floor",
            "port_roof_to_gasket",
            "gasket_outer_waist_vertical",
            "gasket_inner_land",
        ),
        feature_limits=(("gasket_inner_land", 0.6),),
    )


def resin_water_profile() -> MaterialWallProfile:
    return MaterialWallProfile(
        "Resin wet-end experiment", Process.RESIN_CAST, water_wall_policy()
    )


def slip_cast_water_profile() -> MaterialWallProfile:
    # No clay body, firing schedule, shrinkage or pump-service qualification.
    return MaterialWallProfile(
        "Slip-cast ceramic: unsupported for this pump", Process.SLIP_CAST
    )


def water_hose_terminal(
    d: BlindSupportDimensions,
    size: Optional[CommonHoseSize] = None,
    supported: bool = True,
) -> HoseBarbDimensions:
    selected_id = (
        size.value.id_mm if size is not None else 2 * (d.pump.port_radius + d.back_web)
    )
    if selected_id / 2 - d.pump.port_radius < d.back_web - 1e-9:
        raise ValueError(
            "selected hose ID cannot retain the pump bore and finished-wall budget"
        )
    terminal = HoseBarbDimensions.from_size(
        (
            size.value
            if size is not None
            else HoseSize("material-sized pump hose ID", selected_id)
        ),
        bore_radius=d.pump.port_radius,
        minimum_wall=d.back_web,
        length=26.0,
        barb_height=0.4,
        barb_length=3.0,
        barb_starts=(14.0, 20.0),
        hose_wall=2.0,
        hose_start=9.0,
        clamp_length=5.0,
        clamp_clearance=1.0,
        root_extra_radius=2.5 if supported else 0.0,
        root_length=8.0 if supported else 0.0,
    )
    replace(water_wall_policy(), minimum_mm=d.back_web).require(
        {**d.wall_measurements(), "terminal_wall": terminal.finished_wall}
    )
    return terminal


def water_feature_pump(
    angle: float = 0.0,
    profile: Optional[MaterialWallProfile] = None,
    hose_size: Optional[CommonHoseSize] = None,
    supported_roots: bool = True,
) -> Assembly:
    d = water_pump_dimensions(profile, hose_size)
    g = GearPumpGeometry(**vars(d.pump))
    hose = water_hose_terminal(d, hose_size, supported_roots)
    assembly = Assembly("water_feature_wet_end")
    for kind, color, process, material in [
        (
            "body",
            (72, 144, 170),
            Process.RESIN_CAST,
            "water-compatible resin TBD; finish-machined",
        ),
        (
            "cover",
            (118, 184, 202),
            Process.RESIN_CAST,
            "water-compatible resin TBD; finish-machined",
        ),
        (
            "gasket",
            (76, 78, 82),
            Process.PURCHASED,
            "cut sheet elastomer TBD; installed envelope",
        ),
        (
            "driver_shaft",
            (155, 161, 170),
            Process.ROD_STOCK,
            "corrosion-resistant ground metal TBD",
        ),
        (
            "idler_shaft",
            (155, 161, 170),
            Process.ROD_STOCK,
            "corrosion-resistant ground metal TBD",
        ),
    ]:
        child = assembly.add_subassembly(Assembly(kind, color))
        spec = PartSpec(
            "water_" + kind,
            BlindSupportPart(d, kind, hose if kind == "body" else None, 12.0),
            (process,),
            material,
        )
        x = g.centres if kind == "idler_shaft" else 0.0
        phase = g.idler_phase(angle) if kind == "idler_shaft" else angle
        child.place_world(spec, "water_" + kind, x, 0, 0)
        if kind.endswith("shaft"):
            child.instances[-1].solid = (
                spec.solid().rotate((0, 0, 0), (0, 0, 1), phase).translate((x, 0, 0))
            )
    rotor = PartSpec(
        "water_rotor",
        g.gear(),
        (Process.CNC_PLATE,),
        "water-service engineering polymer TBD",
    )
    pin = PartSpec(
        "water_rotor_pin",
        PumpPart(g, "pin"),
        (Process.ROD_STOCK,),
        "corrosion-resistant metal TBD",
    )
    for name, x, phase, color in [
        ("driver", 0.0, angle, (232, 165, 67)),
        ("idler", g.centres, g.idler_phase(angle), (187, 103, 90)),
    ]:
        child = assembly.add_subassembly(Assembly(name, color))
        child.place_world(rotor, name, x, 0, g.base + g.face_clearance)
        child.instances[-1].solid = (
            rotor.solid()
            .rotate((0, 0, 0), (0, 0, 1), phase)
            .translate((x, 0, g.base + g.face_clearance))
        )
        child.place_world(pin, name + "_pin", x, 0, 0)
        child.instances[-1].solid = (
            pin.solid().rotate((0, 0, 0), (0, 0, 1), phase).translate((x, 0, 0))
        )
    assembly.hardware.extend(
        [
            HardwareItem(
                f"{hose.hose_id:g} mm ID x {hose.hose_id + 2 * hose.hose_wall:g} mm OD flexible water hose",
                2,
                "Provisional silicone or equivalent; grade, collapse resistance and routing TBD",
            ),
            HardwareItem(
                "hose clamp",
                2,
                f"{hose.clamp_length:g} mm axial land; <={2 * hose.access_radius:g} mm swept OD envelope; select non-cutting clamp and qualify torque",
            ),
            HardwareItem(
                "case clamp bolt / nut / washer sets",
                4,
                "3.3 mm through holes; select length and torque after gasket qualification",
            ),
            HardwareItem(
                "water-rated rotary shaft seal",
                1,
                "UNSELECTED: provisional 6 mm shaft / 12 mm OD / 4 mm width seat",
            ),
            HardwareItem(
                "dry coupling and axial retention",
                1,
                "UNSELECTED: prevent shaft travel and shield rotating parts",
            ),
        ]
    )
    return assembly
