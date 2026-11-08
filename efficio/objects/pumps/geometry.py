"""Pure sizing and interface validation for reusable pump prototypes."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GearPumpDimensions:
    # Gear system / running fits (candidate dimensions, not manufacturing tolerances).
    module: float = 1.0
    teeth: int = 12
    width: float = 6.0
    backlash: float = 0.05
    tip_clearance: float = 0.15
    face_clearance: float = 0.10
    shaft_diameter: float = 4.0
    journal_clearance: float = 0.10
    # Housing, fastening and fluid interfaces.
    wall: float = 5.0
    base: float = 3.0
    cover: float = 3.0
    port_radius: float = 1.5
    port_drop: float = 0.0
    bolt_radius: float = 1.65
    seal_pocket_radius: float = 3.5
    seal_pocket_depth: float = 1.0
    shaft_extension: float = 21.0
    idler_extension: float = 2.5
    collar_thickness: float = 2.0
    collar_radius: float = 4.0
    set_screw_radius: float = 0.8
    rear_extension: float = 2.5
    rotor_pin_diameter: float = 1.0
    rotor_pin_length: float = 5.0
    collar_gap: float = 0.05

    def __post_init__(self) -> None:
        self._validate()

    def problems(self) -> list[str]:
        try:
            self._validate()
        except ValueError as error:
            return [str(error)]
        return []

    def _validate(self) -> None:
        values = [v for k, v in vars(self).items() if k not in {"teeth", "port_drop"}]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("pump dimensions must be finite and positive")
        if (
            not math.isfinite(self.port_drop)
            or not 0
            <= self.port_drop
            < self.width / 2 + self.face_clearance - self.port_radius
        ):
            raise ValueError("port drop must leave its bore inside the chamber height")
        if (
            isinstance(self.teeth, bool)
            or not isinstance(self.teeth, int)
            or self.teeth < 12
        ):
            raise ValueError("pump requires at least twelve teeth")
        if (
            min(self.idler_extension, self.rear_extension)
            < self.collar_gap + self.collar_thickness
        ):
            raise ValueError("idler shaft cannot carry retention collar")
        if (
            self.collar_radius <= self.shaft_diameter / 2 + 0.1
            or self.set_screw_radius * 2 >= self.collar_thickness
        ):
            raise ValueError("collar has insufficient web")
        if (
            self.collar_radius <= self.seal_pocket_radius
            or self.collar_gap >= self.face_clearance
        ):
            raise ValueError(
                "collar must bridge seal pocket and stop before rotor face contact"
            )
        if self.shaft_diameter / 2 + 0.1 >= self.module * (self.teeth / 2 - 1.25):
            raise ValueError("shaft bore consumes tooth root")
        if self.port_radius >= self.tip_radius / 2 or self.wall <= 2 * self.bolt_radius:
            raise ValueError("ports or fasteners consume housing land")
        if (
            not self.shaft_diameter / 2
            < self.seal_pocket_radius
            < self.module * (self.teeth / 2 - 1.25)
        ):
            raise ValueError("seal pocket must fit inside root circle")
        if self.seal_pocket_depth >= min(self.base, self.cover):
            raise ValueError("seal pocket consumes journal")
        if (
            self.tip_clearance >= self.module / 2
            or self.face_clearance >= self.width / 4
        ):
            raise ValueError("running gap is too large for this pump candidate")

    def idler_phase(self, driver_angle: float) -> float:
        # Keep shaft/D-flat phase continuous, not merely tooth-equivalent.
        return (180 + 180 / self.teeth) % (360 / self.teeth) - driver_angle

    @property
    def centres(self) -> float:
        return self.module * self.teeth

    @property
    def tip_radius(self) -> float:
        return self.module * (self.teeth / 2 + 1)

    @property
    def radius(self) -> float:
        return self.tip_radius + self.tip_clearance

    @property
    def half_height(self) -> float:
        return self.radius + self.wall

    @property
    def depth(self) -> float:
        return self.base + self.width + 2 * self.face_clearance

    @property
    def bolt_points(self) -> list[tuple[float, float]]:
        return [
            (x, y)
            for x in (
                -self.radius - self.wall / 2,
                self.centres + self.radius + self.wall / 2,
            )
            for y in (
                -self.half_height + self.wall / 2,
                self.half_height - self.wall / 2,
            )
        ]

    def port(self, sign: int) -> tuple[float, float, float]:
        return (
            self.centres / 2,
            sign * self.half_height,
            self.base + self.width / 2 + self.face_clearance - self.port_drop,
        )


@dataclass(frozen=True)
class StrainerGeometry:
    radius: float
    wall: float
    length: float
    end_wall: float
    port_radius: float
    screen_thickness: float
    hole_radius: float
    hole_circle: float
    hole_count: int

    def __post_init__(self) -> None:
        self._validate()

    def problems(self) -> list[str]:
        try:
            self._validate()
        except ValueError as error:
            return [str(error)]
        return []

    def _validate(self) -> None:
        if not all(math.isfinite(v) and v > 0 for v in vars(self).values()):
            raise ValueError("strainer dimensions must be positive and finite")
        if not isinstance(self.hole_count, int) or self.hole_count < 3:
            raise ValueError("screen needs at least three circumferential holes")
        if (
            self.port_radius >= self.radius - self.wall
            or 2 * self.end_wall + self.screen_thickness >= self.length
        ):
            raise ValueError("strainer chamber is consumed")
        if (
            self.hole_circle + self.hole_radius >= self.radius - self.wall
            or self.hole_circle <= 2 * self.hole_radius
        ):
            raise ValueError("screen holes consume rim or central web")
        if (
            2 * self.hole_circle * math.sin(math.pi / self.hole_count)
            <= 2 * self.hole_radius
        ):
            raise ValueError("screen holes overlap")


@dataclass(frozen=True)
class BlindSupportDimensions:
    pump: GearPumpDimensions
    back_web: float
    front_web: float
    end_gap: float
    seal_radius: float
    seal_depth: float
    gasket_width: float
    gasket_inset: float
    gasket_depth: float
    shaft_radius: float
    exterior_offset: float = 0.0
    boss_radius: float = 0.0
    bevel: float = 0.0

    def __post_init__(self) -> None:
        errors = self.problems()
        if errors:
            raise ValueError(errors[0])

    def problems(self) -> list[str]:
        g = self.pump
        values = [
            v
            for k, v in vars(self).items()
            if k not in {"pump", "exterior_offset", "boss_radius", "bevel"}
        ]
        if not all(math.isfinite(v) and v > 0 for v in values):
            return ["wet-end dimensions must be positive and finite"]
        if not all(
            math.isfinite(v) and v >= 0
            for v in (self.exterior_offset, self.boss_radius, self.bevel)
        ):
            return ["exterior offsets must be finite and nonnegative"]
        if self.exterior_offset:
            if self.boss_radius <= g.bolt_radius + self.bevel:
                return ["beveled boss consumes bolt web"]
            if self.exterior_offset <= self.bevel or self.bevel >= min(g.base, g.cover):
                return ["bevel consumes wall or end plate"]
            if (g.radius + self.exterior_offset) ** 2 <= (g.centres / 2) ** 2:
                return ["offset envelope does not enclose waist"]
            if min(self.wall_measurements().values()) <= 0:
                return ["organic exterior consumes a functional interface"]
        elif self.boss_radius or self.bevel:
            return ["bosses and bevel require an organic offset"]
        if not self.shaft_radius < g.shaft_diameter / 2 + g.journal_clearance:
            return ["shaft consumes journal clearance"]
        if self.back_web + self.end_gap >= g.base:
            return ["rear blind support too shallow"]
        if self.front_web + self.end_gap >= g.cover:
            return ["idler blind support too shallow"]
        if self.seal_depth >= g.cover or self.seal_radius <= g.shaft_diameter / 2:
            return ["seal seat consumes cover journal"]
        if self.seal_radius >= g.centres - g.shaft_diameter / 2 - g.journal_clearance:
            return ["seal seat intersects idler support"]
        if self.gasket_depth >= g.face_clearance + g.width:
            return ["gasket groove consumes body"]
        if self.gasket_inset + self.gasket_width >= g.wall / 2 - g.bolt_radius:
            return ["gasket intersects bolt holes"]
        if g.wall / 2 <= g.bolt_radius:
            return ["bolt holes consume capsule wall"]
        return []

    @property
    def bolt_points(self) -> list[tuple[float, float]]:
        g = self.pump
        q = (g.radius + g.wall / 2) / math.sqrt(2)
        return [(-q, -q), (-q, q), (g.centres + q, -q), (g.centres + q, q)]

    def wall_measurements(self) -> dict[str, float]:
        """Analytical feature bounds for the organic envelope; not global FEA.

        Waist uses vertical clearance to the retained capsule gasket (a local
        thickness, not a global shortest-distance claim). Boss additions only
        increase the base offset envelope; outer end bevel is bounded by its
        specified radial inset. Intended openings and mating contacts excluded.
        """
        g = self.pump
        radius = g.radius + self.exterior_offset
        waist = math.sqrt(max(0.0, radius * radius - (g.centres / 2) ** 2))
        return {
            "offset_side_wall": self.exterior_offset,
            "beveled_offset_bound": self.exterior_offset - self.bevel,
            "bolt_boss_ligament": self.boss_radius - g.bolt_radius - self.bevel,
            "bolt_to_chamber": g.wall / 2 - g.bolt_radius,
            "rear_blind_floor": self.back_web,
            "idler_cover_floor": self.front_web,
            "seal_seat_floor": g.cover - self.seal_depth,
            "port_roof_to_gasket": g.width / 2
            + g.face_clearance
            + g.port_drop
            - g.port_radius
            - self.gasket_depth,
            "gasket_outer_waist_vertical": waist
            - g.radius
            - self.gasket_inset
            - self.gasket_width,
            "gasket_inner_land": self.gasket_inset,
        }
