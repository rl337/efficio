"""Editable, separate-parts educational engine; fluid function is undecided."""

from efficio.examples.drivetrain import add_engine
from efficio.examples.drivetrain_groups import group_engine
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.fits import Process
from efficio.objects.powertrain.engine import EngineGeometry
from efficio.objects.powertrain.engine.resin import (
    ResinEngineHousingPart,
    ResinHousingGeometry,
    ResinHousingPart,
)
from efficio.objects.powertrain.layout import DrivetrainLayout


def resin_engine_geometry() -> ResinHousingGeometry:
    return ResinHousingGeometry(
        EngineGeometry(bore=30, stroke=26, rod_length=52, cylinder_spacing=40)
    )


def resin_engine_assembly(crank_angle: float = 30.0) -> Assembly:
    geometry = resin_engine_geometry()
    root = Assembly("Educational resin engine")
    add_engine(root, DrivetrainLayout(engine=geometry.engine), crank_angle)
    group_engine(root, geometry.engine.cylinders)
    housing = root.find("Housing")
    bearings = [
        h for h in housing.hardware if h.notes == "Crank mains in block end walls"
    ]
    housing.parts.clear()
    housing.instances.clear()
    housing.hardware.clear()
    # The standalone housing has no validated connection to the gearbox yet.
    mounts = root.find("Engine mounts")
    root.children.remove(mounts)
    mounts.parent = None
    groups = [
        (
            "Cylinder liners",
            ResinHousingPart.LINER,
            (58, 120, 160),
            "Opaque resin candidate; continuous wall; bore finishing undecided",
        ),
        (
            "Liner deck",
            ResinHousingPart.DECK,
            (82, 149, 128),
            "Colored resin candidate; flanged seats; seal and fastener design pending",
        ),
        (
            "Head",
            ResinHousingPart.HEAD,
            (164, 71, 67),
            "Colored resin candidate; no valves or cooling passages",
        ),
        (
            "Coolant jacket",
            ResinHousingPart.JACKET,
            (155, 209, 223),
            "Clear resin candidate; actual cavity and two open ports; seals pending",
        ),
        (
            "Front bearing support",
            ResinHousingPart.FRONT_SUPPORT,
            (133, 114, 154),
            "Colored resin candidate; existing upper bearing seat",
        ),
        (
            "Rear bearing support",
            ResinHousingPart.REAR_SUPPORT,
            (133, 114, 154),
            "Colored resin candidate; existing upper bearing seat",
        ),
        (
            "Lower bearing frame",
            ResinHousingPart.BEARING_FRAME,
            (117, 103, 139),
            "Colored resin candidate; lower bearing seats and side rails",
        ),
        (
            "Oil pan",
            ResinHousingPart.OIL_PAN,
            (174, 214, 202),
            "Clear resin candidate; cavity and open drain; no seal or oil feed network",
        ),
    ]
    for name, kind, color, note in groups:
        child = housing.add_subassembly(Assembly(name, color))
        spec = PartSpec(
            "resin_" + kind.value,
            ResinEngineHousingPart(geometry, kind),
            (Process.RESIN_CAST,),
            "resin candidate",
            note,
        )
        for i in range(
            geometry.engine.cylinders if kind is ResinHousingPart.LINER else 1
        ):
            y = geometry.engine.cylinder_y(i) if kind is ResinHousingPart.LINER else 0
            child.place_world(
                spec,
                spec.name + (f"_{i}" if kind is ResinHousingPart.LINER else ""),
                0,
                y,
                0,
            )
        if kind is ResinHousingPart.BEARING_FRAME:
            child.hardware.extend(bearings)
    # Differentiate rods from pistons via occurrence groups, not part geometry.
    for i in range(geometry.engine.cylinders):
        unit = root.find(f"Piston and rod {i+1}")
        unit.group_instances("Piston", [f"piston_{i}"], (223, 172, 55))
        unit.group_instances(
            "Rod and pin", [f"connecting_rod_{i}", f"wrist_pin_{i}"], (64, 157, 132)
        )
    for name in ("piston", "connecting_rod", "crank_web", "flywheel"):
        spec = root.all_parts()[name]
        spec.processes = (Process.RESIN_CAST,)
        spec.material = "colored resin candidate"
        spec.notes += "; casting, wear and fit qualification pending"
    return root
