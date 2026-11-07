"""Independent water-feature wet-end experiment; no engine dependency."""

import math
from typing import Optional

from efficio.objects.assembly import Assembly, HardwareItem, PartSpec
from efficio.objects.fits import Process
from efficio.objects.pumps.blind_support import BlindSupportPart
from efficio.objects.pumps.external_gear import GearPumpGeometry, PumpPart
from efficio.objects.pumps.geometry import BlindSupportDimensions
from efficio.objects.walls import MaterialWallProfile, WallPolicy


def water_pump_dimensions(
    profile: Optional[MaterialWallProfile] = None,
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
        seal_pocket_radius=4,
        collar_radius=5,
        shaft_extension=18,
        rotor_pin_diameter=1.5,
        rotor_pin_length=7.5,
    )
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
            "port_roof_to_joint",
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


def water_feature_pump(
    angle: float = 0.0, profile: Optional[MaterialWallProfile] = None
) -> Assembly:
    d = water_pump_dimensions(profile)
    g = GearPumpGeometry(**vars(d.pump))
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
            "water_" + kind, BlindSupportPart(d, kind), (process,), material
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
