"""Editable lubrication review: continuous real passages, external pump undecided."""

from efficio.examples.resin_engine import resin_engine_assembly, resin_engine_geometry
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.fits import Process
from efficio.objects.powertrain.engine.lubrication import (
    LubricationGeometry,
    LubricationSump,
)


def lubrication_geometry() -> LubricationGeometry:
    return LubricationGeometry(resin_engine_geometry())


def lubricated_engine_assembly(crank_angle: float = 30.0) -> Assembly:
    root = resin_engine_assembly(crank_angle)
    g = lubrication_geometry()
    pan = root.find("Oil pan")
    pan.instances.clear()
    pan.parts.clear()
    spec = PartSpec(
        "resin_oil_pan",
        LubricationSump(g),
        (Process.RESIN_CAST,),
        "clear resin candidate",
        "Crankcase/pan enclosure; shaft/service openings and drain; seals, drain closure and clamps unresolved",
    )
    pan.place_world(spec, "resin_oil_pan", 0, 0, 0)
    oil = root.add_subassembly(Assembly("Lubrication"))
    for name, obj, color, note in [
        (
            "Oil pickup",
            g.pickup(),
            (210, 154, 44),
            "Open pickup 2 mm above floor to external suction interface; screen and fitting design pending",
        ),
        (
            "Oil supply",
            g.supply(),
            (190, 110, 30),
            "External pressure interface to four under-liner nozzles and two bearing-face outlets; no drilled crank feeds or sealed-bearing compatibility claim",
        ),
    ]:
        group = oil.add_subassembly(Assembly(name, color))
        spec = PartSpec(
            name.lower().replace(" ", "_"),
            obj,
            (Process.RESIN_CAST,),
            "tube/manifold material undecided",
            note + "; CAD bore network, fabrication unqualified",
        )
        group.place_world(spec, spec.name, 0, 0, 0)
    return root
