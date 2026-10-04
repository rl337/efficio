import logging
import math
from enum import Enum
from typing import List, Optional, Tuple, Type  # Removed cast

import cadquery as cq

from efficio.measures import CompoundMeasure, Measure, Millimeter
from efficio.objects import primitives
from efficio.objects.base import EfficioObject
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape, new_shape


class AbstractRotaryDriver(EfficioObject):
    _maximum_radius: Measure
    _thickness: Measure

    """Abstract base class for any rotating object that transfers motion."""

    def __init__(self, maximum_radius: Measure, thickness: Measure):
        super().__init__()
        self._maximum_radius = maximum_radius
        self._thickness = thickness

    def get_maximum_radius(self) -> Measure:
        return self._maximum_radius

    def get_thickness(self) -> Measure:
        return self._thickness


class AbstractCogwheel(AbstractRotaryDriver):
    """Represents any rotating driver that engages via teeth."""

    _tooth_count: int

    def __init__(self, maximum_radius: Measure, tooth_count: int, thickness: Measure):
        super().__init__(maximum_radius, thickness)
        self._tooth_count = tooth_count

    def get_tooth_count(self) -> int:
        return self._tooth_count


class AbstractSprocket(AbstractCogwheel):
    """A sprocket that engages with a chain or track instead of another gear."""

    pass  # Placeholder for future functionality


class AbstractPulley(AbstractRotaryDriver):
    """A pulley that transfers motion via friction (e.g., belt drives)."""

    pass  # Placeholder for future functionality


class GearStandard(Enum):

    def pitch_radius(self, num_teeth: int) -> float:
        """
        Compute the pitch radius based on whether the gear is metric (module) or imperial (DP).
        - For metric gears: R_p = (m * N) / 2
        - For diametral pitch gears: R_p = (N / (2 * DP))
        """
        if isinstance(self, MetricModule):
            return float(self.value * num_teeth) / 2
        elif isinstance(self, DiametralPitch):
            return float(num_teeth / (2 * self.value))
        else:
            raise ValueError("Invalid gear standard type")

    def addendum_radius(self, num_teeth: int) -> float:
        pitch_radius = self.pitch_radius(num_teeth)
        if isinstance(self, MetricModule):
            return float(pitch_radius + self.value)
        elif isinstance(self, DiametralPitch):
            return float(pitch_radius + 1 / self.value)
        else:
            raise ValueError("Invalid gear standard type")


# 📏 **Metric (ISO) Gear Modules**
class MetricModule(GearStandard):
    MODULE_0_8 = 0.8
    MODULE_1 = 1.0
    MODULE_1_25 = 1.25
    MODULE_1_5 = 1.5
    MODULE_2 = 2.0
    MODULE_2_5 = 2.5
    MODULE_3 = 3.0
    MODULE_4 = 4.0

    # Aliases for 3D printing
    MODULE_FINE = MODULE_1
    MODULE_NORMAL = MODULE_1_5
    MODULE_LARGE = MODULE_2

    @staticmethod
    def examples() -> List[str]:
        return [
            "MODULE_FINE",
            "MODULE_NORMAL",
            "MODULE_LARGE",
            "MODULE_1",
            "MODULE_1_5",
            "MODULE_2",
        ]


# ⚙️ **Imperial (AGMA) Diametral Pitch (DP)**
class DiametralPitch(GearStandard):
    PITCH_24 = 24
    PITCH_20 = 20
    PITCH_16 = 16
    PITCH_14 = 14
    PITCH_12 = 12
    PITCH_10 = 10

    # Aliases for 3D printing
    PITCH_FINE = PITCH_20
    PITCH_NORMAL = PITCH_16
    PITCH_LARGE = PITCH_12

    @staticmethod
    def examples() -> List[str]:
        return [
            "PITCH_FINE",
            "PITCH_NORMAL",
            "PITCH_LARGE",
            "PITCH_20",
            "PITCH_16",
            "PITCH_12",
        ]


class PressureAngle(Enum):
    """
    Pressure angle is the angle between the line of action and the line normal to the gear surface.
    """

    MODERN = 20
    OLD = 14.5
    HIGH_TORQUE = 25

    @staticmethod
    def examples() -> List[str]:
        return ["MODERN", "OLD", "HIGH_TORQUE"]


class AbstractGearTooth(EfficioObject):
    gear: "AbstractGear"

    def __init__(self, gear: "AbstractGear"):
        self.gear = gear

    def calculate_pitch_angle(self) -> float:
        """
        The pitch angle is the angle formed by drawing lines from the center of the gear to the points of contact between the gear and its mating gear.
        """
        return 2 * math.pi / self.gear.get_tooth_count()

    def calculate_pitch_radius(self) -> float:
        """
        The pitch radius of a gear is the radius of the circle that passes through the points of contact between the gear and its mating gear.
        """
        raise NotImplementedError("AbstractGearTooth::calculate_pitch_radius()")

    def calculate_addendum(self) -> float:
        """
        The addendum radius is the radius of the circle that passes through the points of the top of the gear tooth sides.
        """
        raise NotImplementedError("AbstractGearTooth::calculate_addendum_radius()")

    def calculate_dedendum(self) -> float:
        """
        The dedendum radius is the radius of the circle that passes through the points of the bottom of the gear tooth sides.
        """
        raise NotImplementedError("AbstractGearTooth::calculate_dedendum_radius()")

    def calculate_circular_pitch(self) -> float:
        """
        The circular pitch is the distance between corresponding points on adjacent teeth along the pitch circle. Here
        the pitch circle is circular distance between the centers of two adjacent teeth.
        """
        return self.calculate_pitch_radius() * self.calculate_pitch_angle()

    def calculate_tooth_height(self) -> float:
        return self.calculate_dedendum() + self.calculate_addendum()

    def calculate_tooth_width(self) -> float:
        """
        The tooth width is the distance between the tip of one gear tooth and the tip of the next gear tooth.
        """
        raise NotImplementedError("AbstractGearTooth::get_tooth_width()")

    def get_thickness(self) -> float:
        """
        The thickness of the gear is the distance between the top of the gear and the bottom of the gear.
        """
        return self.gear.get_thickness().value()

    def get_maximum_radius(self) -> float:
        """
        The maximum radius of the gear is the radius of the circle that passes through the points of the gear.
        """
        return self.gear.get_maximum_radius().value()

    def calculate_base_radius(self) -> float:
        """
        The base radius is the radius of the circle that passes through the points of the base of the gear tooth.
        """
        return self.get_maximum_radius() - self.calculate_tooth_height()

    def calculate_chord_width(self) -> float:
        """
        The chord width is the straight line distance between the start of one tooth and the end of the next tooth.
        """
        return (
            2
            * self.calculate_pitch_radius()
            * math.sin(self.calculate_pitch_angle() / 2)
        )

    def calculate_max_chord_width(self) -> float:
        return (
            2 * self.get_maximum_radius() * math.sin(self.calculate_pitch_angle() / 2)
        )

    def calculate_base_chord_width(self) -> float:
        return (
            2
            * self.calculate_base_radius()
            * math.sin(self.calculate_pitch_angle() / 2)
        )

    def calculate_addendum_radius(self) -> float:
        return self.calculate_pitch_radius() + self.calculate_addendum()

    def calculate_dedendum_radius(self) -> float:
        return self.calculate_pitch_radius() - self.calculate_dedendum()


class AbstractTrapezoidalGearTooth(AbstractGearTooth):
    _top_width_ratio: float

    def __init__(self, gear: "AbstractGear", top_width_ratio: float):
        super().__init__(gear)
        self._top_width_ratio = top_width_ratio

    def calculate_pitch_radius(self) -> float:
        return self.gear.get_maximum_radius().value() * 0.85

    def calculate_addendum(self) -> float:
        return self.calculate_circular_pitch() * 0.7 * 2.0 / 3.0

    def calculate_dedendum(self) -> float:
        return self.calculate_circular_pitch() * 0.7 / 3.0

    def calculate_tooth_width(self) -> float:
        return self.calculate_chord_width() / 2

    def calculate_top_width(self) -> float:
        return self.calculate_tooth_width() * self._top_width_ratio

    def calculate_base_radius(self) -> float:
        """
        The base radius is the radius of the circle that passes through the points of the base of the gear tooth.
        It's calculated by subtracting the max radius from the height of the tooth.  We need to adjust for the fact
        that the max circle doesn't pass through the center of the top of the tooth.
        We need to also adjust for the fact that the base circle doesn't pass through the center of the bottom of the tooth.
        """
        cos_of_pitch_angle = math.cos(self.calculate_pitch_angle() / 2)
        top_of_tooth_radius = cos_of_pitch_angle * self.get_maximum_radius()
        bottom_of_tooth_radius = top_of_tooth_radius - self.calculate_tooth_height()
        bottom_of_tooth_radius_adjustment = (
            bottom_of_tooth_radius - bottom_of_tooth_radius * cos_of_pitch_angle
        )
        return bottom_of_tooth_radius + bottom_of_tooth_radius_adjustment

    def shape(self) -> Optional[Shape]:
        tooth_width_base = self.calculate_tooth_width()
        tooth_height = self.calculate_tooth_height()
        tooth_width_top = tooth_width_base * self._top_width_ratio

        return (
            new_shape(Orientation.Front)
            .polyline(
                [
                    (-tooth_width_base / 2, -tooth_height / 2),
                    (tooth_width_base / 2, -tooth_height / 2),
                    (tooth_width_top / 2, tooth_height / 2),
                    (-tooth_width_top / 2, tooth_height / 2),
                ]
            )
            .extrude(self.get_thickness())
            .translate(0, 0, -self.get_thickness() / 2)
        )


class AbstractSphericalGearTooth(AbstractGearTooth):
    """
    Abstract base class for gear teeth specifically designed for spherical gears.
    These teeth are typically defined by a 2D profile that can be revolved or swept
    along a spherical path.
    """

    def get_spherical_tooth_profile_points(self) -> List[Tuple[float, float]]:
        """
        Returns a list of (x,y) points defining the 2D cross-sectional profile
        of a tooth intended for a spherical gear. The profile is typically
        revolved or used in a sweep operation to form the 3D tooth.

        'x' coordinates generally represent radial distances from the gear's revolution
        axis (or from the center of the sphere if the profile is on the sphere surface).
        'y' coordinates represent distances along that axis (or along the tooth's
        own axis if defined locally).
        """
        raise NotImplementedError(
            "This method should be implemented by subclasses to provide a "
            "2D profile for spherical gear teeth."
        )


class TrapezoidalSphericalGearTooth(
    AbstractTrapezoidalGearTooth, AbstractSphericalGearTooth
):
    """
    A trapezoidal tooth profile specifically for spherical gears.
    This class provides the concrete implementation for generating the
    2D cross-sectional points of a trapezoidal tooth on a sphere.
    """

    def __init__(self, gear: "AbstractGear"):
        # Initialize with a default top_width_ratio, similar to _TrapezoidalGearTooth
        AbstractTrapezoidalGearTooth.__init__(self, gear, top_width_ratio=0.5)
        # AbstractSphericalGearTooth does not have an __init__ that needs explicit calling here,
        # as its direct parent AbstractGearTooth.__init__ is called by AbstractTrapezoidalGearTooth.

    def get_spherical_tooth_profile_points(self) -> List[Tuple[float, float]]:
        tooth_height = self.calculate_tooth_height()
        # calculate_tooth_width() and calculate_top_width() are inherited from AbstractTrapezoidalGearTooth
        base_width = self.calculate_tooth_width()
        top_width = self.calculate_top_width()

        # gear_radius is the maximum radius of the sphere (to the tooth tip).
        gear_radius = self.gear.get_maximum_radius().value()

        # r_base is the radius at the root of the tooth.
        r_base = gear_radius - tooth_height

        # Define the 2D profile points.
        # 'x' is the radial distance from the gear center.
        # 'y' is the half-width of the tooth profile segment.
        points = [
            (r_base, -base_width / 2),  # P1: Base of the tooth, one side
            (gear_radius, -top_width / 2),  # P2: Tip of the tooth, same side
            (gear_radius, top_width / 2),  # P3: Tip of the tooth, other side
            (r_base, base_width / 2),  # P4: Base of the tooth, other side
        ]
        return points


class _TrapezoidalGearTooth(AbstractTrapezoidalGearTooth):
    def __init__(self, gear: "AbstractGear"):
        super().__init__(gear, 0.5)


class _RectangularGearTooth(AbstractTrapezoidalGearTooth):
    def __init__(self, gear: "AbstractGear"):
        super().__init__(gear, 1.0)


class InvoluteGearToothProfile:
    """Reusable standard full-depth involute tooth profile.

    Efficio gear constructors historically specify the outside (addendum)
    radius.  The equivalent module is therefore derived from
    outside_diameter = module * (tooth_count + 2).
    """

    def __init__(
        self,
        maximum_radius: float,
        tooth_count: int,
        pressure_angle: PressureAngle = PressureAngle.MODERN,
    ):
        if tooth_count < 4:
            raise ValueError("Involute profiles require at least four teeth")
        self.maximum_radius = float(maximum_radius)
        self.tooth_count = tooth_count
        self.pressure_angle = pressure_angle

    @property
    def module(self) -> float:
        return 2.0 * self.maximum_radius / (self.tooth_count + 2)

    @property
    def pitch_radius(self) -> float:
        return self.module * self.tooth_count / 2.0

    @property
    def addendum_radius(self) -> float:
        return self.pitch_radius + self.module

    @property
    def root_radius(self) -> float:
        return max(self.pitch_radius - 1.25 * self.module, self.module * 0.05)

    @property
    def base_radius(self) -> float:
        return self.pitch_radius * math.cos(math.radians(self.pressure_angle.value))

    @staticmethod
    def involute_angle(parameter: float) -> float:
        """Angular displacement along an involute: inv(t) = t - atan(t)."""
        return parameter - math.atan(parameter)

    def parameter_at_radius(self, radius: float) -> float:
        if radius < self.base_radius:
            raise ValueError("The involute is undefined below its base circle")
        return math.sqrt(max((radius / self.base_radius) ** 2 - 1.0, 0.0))

    def half_tooth_angle_at_pitch(self) -> float:
        return math.pi / (2.0 * self.tooth_count)

    def flank_point(self, radius: float, side: int) -> Tuple[float, float]:
        """Return a point on the left (-1) or right (+1) involute flank."""
        if side not in (-1, 1):
            raise ValueError("side must be -1 or +1")
        parameter = self.parameter_at_radius(radius)
        pitch_parameter = self.parameter_at_radius(self.pitch_radius)
        pitch_involute = self.involute_angle(pitch_parameter)
        point_involute = self.involute_angle(parameter)
        angle = side * (
            self.half_tooth_angle_at_pitch() + pitch_involute - point_involute
        )
        return radius * math.cos(angle), radius * math.sin(angle)

    def tooth_outline(self, flank_samples: int = 10) -> List[Tuple[float, float]]:
        """Sample one symmetric tooth suitable for extrusion or future sweeps."""
        if flank_samples < 2:
            raise ValueError("flank_samples must be at least two")
        start_radius = max(self.base_radius, self.root_radius)
        radii = [
            start_radius
            + (self.addendum_radius - start_radius) * index / flank_samples
            for index in range(flank_samples + 1)
        ]
        right = [self.flank_point(radius, 1) for radius in radii]
        left = [self.flank_point(radius, -1) for radius in reversed(radii)]

        right_angle = math.atan2(right[0][1], right[0][0])
        left_angle = math.atan2(left[-1][1], left[-1][0])
        right_root = (
            self.root_radius * math.cos(right_angle),
            self.root_radius * math.sin(right_angle),
        )
        left_root = (
            self.root_radius * math.cos(left_angle),
            self.root_radius * math.sin(left_angle),
        )
        return [right_root] + right + left + [left_root]


class _InvoluteGearTooth(AbstractGearTooth):
    def __init__(
        self,
        gear: "AbstractGear",
        pressure_angle: PressureAngle = PressureAngle.MODERN,
    ):
        super().__init__(gear)
        self.profile = InvoluteGearToothProfile(
            gear.get_maximum_radius().value(),
            gear.get_tooth_count(),
            pressure_angle,
        )

    def calculate_pitch_radius(self) -> float:
        return self.profile.pitch_radius

    def calculate_addendum(self) -> float:
        return self.profile.addendum_radius - self.profile.pitch_radius

    def calculate_dedendum(self) -> float:
        return self.profile.pitch_radius - self.profile.root_radius

    def calculate_tooth_width(self) -> float:
        return self.calculate_circular_pitch() / 2.0

    def calculate_base_radius(self) -> float:
        return self.profile.root_radius

    def shape(self) -> Optional[Shape]:
        return (
            new_shape(Orientation.Front)
            .polyline(self.profile.tooth_outline())
            .extrude(self.get_thickness())
            .translate(0, 0, -self.get_thickness() / 2.0)
        )


class GearToothType(Enum):
    gear_tooth_class: Type[AbstractGearTooth]
    index: int

    def __init__(self, index: int, gear_tooth_class: Type[AbstractGearTooth]):
        self.index = index
        self.gear_tooth_class = gear_tooth_class

    RECTANGULAR = (0, _RectangularGearTooth)
    TRAPEZOIDAL = (1, _TrapezoidalGearTooth)
    INVOLUTE = (2, _InvoluteGearTooth)
    SPHERICAL_TRAPEZOIDAL = (3, TrapezoidalSphericalGearTooth)


class AbstractGear(AbstractCogwheel):
    _gear_tooth_type: GearToothType

    def __init__(
        self,
        maximum_radius: Measure,
        tooth_count: int,
        thickness: Measure,
        gear_tooth_type: GearToothType,
    ):
        super().__init__(maximum_radius, tooth_count, thickness)

        self._gear_tooth_type = gear_tooth_type

    def shape(self) -> Optional[Shape]:
        tooth_object = self._gear_tooth_type.gear_tooth_class(self)
        max_radius = tooth_object.get_maximum_radius()
        base_radius = tooth_object.calculate_base_radius()

        min_radius_adjustment = base_radius - base_radius * math.cos(
            tooth_object.calculate_pitch_angle() / 2
        )
        gear = (
            new_shape(Orientation.Front)
            .circle(base_radius)
            .extrude(self.get_thickness().value())
        )

        tooth_height = tooth_object.calculate_tooth_height()
        translation_distance = max_radius - tooth_height / 2 - min_radius_adjustment
        for i in range(self.get_tooth_count()):
            tooth_shape = tooth_object.shape()
            if tooth_shape is None:
                continue
            x_offset = translation_distance * math.sin(
                i * tooth_object.calculate_pitch_angle()
            )
            y_offset = translation_distance * math.cos(
                i * tooth_object.calculate_pitch_angle()
            )
            tooth_shape.rotate(0, 0, -i * 360 / self.get_tooth_count()).translate(
                x_offset, y_offset, self.get_thickness().value() / 2
            )
            gear = gear.union(tooth_shape)

        return gear


class RectangularGear(AbstractGear):
    def __init__(self, radius: Measure, tooth_count: int, thickness: Measure):
        super().__init__(radius, tooth_count, thickness, GearToothType.RECTANGULAR)


class TrapezoidalGear(AbstractGear):
    def __init__(self, radius: Measure, tooth_count: int, thickness: Measure):
        super().__init__(radius, tooth_count, thickness, GearToothType.TRAPEZOIDAL)


class InvoluteGear(AbstractGear):
    """Standard full-depth involute spur gear."""

    def __init__(
        self,
        radius: Measure,
        tooth_count: int,
        thickness: Measure,
        pressure_angle: PressureAngle = PressureAngle.MODERN,
    ):
        super().__init__(radius, tooth_count, thickness, GearToothType.INVOLUTE)
        self.pressure_angle = pressure_angle

    def shape(self) -> Optional[Shape]:
        profile = InvoluteGearToothProfile(
            self.get_maximum_radius().value(),
            self.get_tooth_count(),
            self.pressure_angle,
        )
        thickness = self.get_thickness().value()
        gear = new_shape(Orientation.Front).circle(profile.root_radius).extrude(thickness)

        for index in range(self.get_tooth_count()):
            tooth = (
                new_shape(Orientation.Front)
                .polyline(profile.tooth_outline())
                .extrude(thickness)
                .rotate(0, 0, index * 360.0 / self.get_tooth_count())
            )
            gear = gear.union(tooth)
        return gear


class _SphericalGearAxis(AbstractGear):
    _axis: str

    def __init__(self, radius: Measure, tooth_count: int, axis: str):
        super().__init__(radius, tooth_count, Millimeter(1), GearToothType.TRAPEZOIDAL)
        self._axis = axis

    def shape(self) -> Optional[Shape]:
        this_shape = super().shape()
        assert this_shape is not None
        if self._axis == "X":
            return this_shape.revolve(180, (0, 0, 0), (0, 1, 0))
        elif self._axis == "Y":
            return this_shape.revolve(180, (0, 0, 0), (1, 0, 0))
        elif self._axis == "Z":
            return this_shape.revolve(180, (0, 0, 0), (0, 0, 1))
        else:
            raise ValueError(f"Invalid axis: {self._axis}")


class SphericalGear(AbstractGear):
    """A gear whose teeth are a continuous periodic displacement of a sphere.

    Three orthogonal angular tooth families modulate the radius of the surface.
    Unlike attaching prismatic teeth to great-circle bands, every generated
    surface point is displaced along its local spherical normal.  Intersections
    between the families therefore form the characteristic wave pattern of a
    spherical gear while the requested maximum radius remains a hard envelope.
    """

    _TOOTH_HEIGHT_RATIO = 0.10
    _LATITUDE_SEGMENTS = 48
    _LONGITUDE_SEGMENTS_PER_TOOTH = 8

    def __init__(self, radius: Measure, tooth_count: int):
        if tooth_count < 4:
            raise ValueError("SphericalGear requires at least four teeth")
        super().__init__(
            radius, tooth_count, Millimeter(1), GearToothType.SPHERICAL_TRAPEZOIDAL
        )

    def _root_radius(self) -> float:
        return self.get_maximum_radius().value() * (1.0 - self._TOOTH_HEIGHT_RATIO)

    def _tooth_wave(self, phase: float) -> float:
        """Smooth periodic tooth height in [0, 1] for an angular phase."""
        return 0.5 + 0.5 * math.cos(self.get_tooth_count() * phase)

    def _surface_radius(self, x: float, y: float, z: float) -> float:
        """Return radial surface distance for a unit direction vector."""
        # Each atan2 is the angular coordinate around one of the three principal
        # axes. Averaging the orthogonal families produces smooth intersections
        # rather than stacked solids and can never exceed the requested tip radius.
        waves = (
            self._tooth_wave(math.atan2(y, x)),
            self._tooth_wave(math.atan2(z, x)),
            self._tooth_wave(math.atan2(z, y)),
        )
        root = self._root_radius()
        height = self.get_maximum_radius().value() - root
        return root + height * sum(waves) / len(waves)

    @staticmethod
    def _triangle(a: cq.Vector, b: cq.Vector, c: cq.Vector) -> cq.Face:
        wire = cq.Wire.makePolygon([a, b, c, a])
        return cq.Face.makeFromWires(wire)

    def _surface_solid(self) -> cq.Solid:
        """Tessellate the radial field into one watertight OpenCascade solid."""
        latitude_segments = self._LATITUDE_SEGMENTS
        longitude_segments = max(
            self.get_tooth_count() * self._LONGITUDE_SEGMENTS_PER_TOOTH, 64
        )

        north_radius = self._surface_radius(0.0, 0.0, 1.0)
        south_radius = self._surface_radius(0.0, 0.0, -1.0)
        north = cq.Vector(0.0, 0.0, north_radius)
        south = cq.Vector(0.0, 0.0, -south_radius)

        rings: List[List[cq.Vector]] = []
        for latitude_index in range(1, latitude_segments):
            theta = math.pi * latitude_index / latitude_segments
            sin_theta = math.sin(theta)
            cos_theta = math.cos(theta)
            ring: List[cq.Vector] = []
            for longitude_index in range(longitude_segments):
                phi = 2 * math.pi * longitude_index / longitude_segments
                direction = (
                    sin_theta * math.cos(phi),
                    sin_theta * math.sin(phi),
                    cos_theta,
                )
                radius = self._surface_radius(*direction)
                ring.append(cq.Vector(*(radius * value for value in direction)))
            rings.append(ring)

        faces: List[cq.Face] = []
        for index in range(longitude_segments):
            following = (index + 1) % longitude_segments
            faces.append(self._triangle(north, rings[0][index], rings[0][following]))

        for ring_index in range(len(rings) - 1):
            upper = rings[ring_index]
            lower = rings[ring_index + 1]
            for index in range(longitude_segments):
                following = (index + 1) % longitude_segments
                a, b = upper[index], upper[following]
                c, d = lower[following], lower[index]
                faces.append(self._triangle(a, c, b))
                faces.append(self._triangle(a, d, c))

        for index in range(longitude_segments):
            following = (index + 1) % longitude_segments
            faces.append(
                self._triangle(rings[-1][index], south, rings[-1][following])
            )

        shell = cq.Shell.makeShell(faces)
        if not shell.Closed():
            raise ValueError("Spherical gear surface did not form a closed shell")
        solid = cq.Solid.makeSolid(shell)
        if not solid.isValid():
            raise ValueError("Spherical gear surface did not form a valid solid")
        return solid

    def shape(self) -> Optional[Shape]:
        workplane_shape = WorkplaneShape(Orientation.Front)
        workplane_shape._workplane = cq.Workplane("XY").newObject([self._surface_solid()])
        return workplane_shape

