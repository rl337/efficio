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
        values = [v for k, v in vars(self).items() if k != "teeth"]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("pump dimensions must be finite and positive")
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
            self.base + self.width / 2 + self.face_clearance,
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
