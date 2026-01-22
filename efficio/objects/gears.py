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


class _InvoluteGearTooth(AbstractGearTooth):
    def calculate_pitch_radius(self) -> float:
        return float(self.gear.get_maximum_radius().value()) * 0.85


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
    def __init__(self, radius: Measure, tooth_count: int):
        super().__init__(
            radius, tooth_count, Millimeter(1), GearToothType.SPHERICAL_TRAPEZOIDAL
        )

    def _create_spherical_tooth(
        self, radius: float, height: float, width_angle: float, theta: float, phi: float
    ) -> Optional[Shape]:
        """
        Creates a single tooth on the sphere surface using spherical coordinates.

        Args:
            radius: Sphere radius
            height: Tooth height (radial distance from sphere surface)
            width_angle: Angular width of the tooth
            theta: Polar angle (0 to π, where π/2 is equator)
            phi: Azimuthal angle (0 to 2π)
        """
        import math

        # Convert spherical to Cartesian coordinates for tooth center
        x_center = radius * math.sin(theta) * math.cos(phi)
        y_center = radius * math.sin(theta) * math.sin(phi)
        z_center = radius * math.cos(theta)

        # Create tooth as a small box oriented toward the sphere center
        tooth_size = radius * 0.05  # Small tooth size

        # Create tooth box
        tooth = new_shape(Orientation.Front).box(tooth_size, tooth_size, height)

        # Position tooth on sphere surface
        tooth = tooth.translate(x_center, y_center, z_center)

        return tooth

    def _generate_spherical_teeth(self) -> Optional[Shape]:
        """
        Generates teeth directly on a sphere surface using proper spherical coordinates.
        This approach avoids complex boolean operations and creates clean geometry.
        """
        import math
        from typing import cast

        from efficio.objects.shapes import WorkplaneShape

        radius_val = self.get_maximum_radius().value()
        tooth_count = self.get_tooth_count()

        # Calculate tooth parameters
        tooth_height = radius_val * 0.1  # 10% of radius
        tooth_width_angle = (
            2 * math.pi / (tooth_count * 2)
        )  # Half the angle between teeth

        # Create base sphere
        base_sphere = new_shape(Orientation.Front).sphere(radius_val)

        # Generate teeth using spherical coordinates
        teeth_shapes = []

        # Create teeth in rings around the sphere
        # Ring 1: Around the equator (z=0)
        for i in range(tooth_count):
            angle = 2 * math.pi * i / tooth_count
            tooth = self._create_spherical_tooth(
                radius_val,
                tooth_height,
                tooth_width_angle,
                math.pi / 2,
                angle,  # theta=90° (equator), phi varies
            )
            if tooth:
                teeth_shapes.append(tooth)

        # Ring 2: Above equator
        for i in range(tooth_count):
            angle = 2 * math.pi * i / tooth_count
            tooth = self._create_spherical_tooth(
                radius_val,
                tooth_height,
                tooth_width_angle,
                math.pi / 2 - math.pi / 6,
                angle,  # 30° above equator
            )
            if tooth:
                teeth_shapes.append(tooth)

        # Ring 3: Below equator
        for i in range(tooth_count):
            angle = 2 * math.pi * i / tooth_count
            tooth = self._create_spherical_tooth(
                radius_val,
                tooth_height,
                tooth_width_angle,
                math.pi / 2 + math.pi / 6,
                angle,  # 30° below equator
            )
            if tooth:
                teeth_shapes.append(tooth)

        # Union all teeth with the base sphere
        if not teeth_shapes:
            return base_sphere

        result = base_sphere
        for tooth in teeth_shapes:
            result = result.union(tooth)

        return result

    def shape(self) -> Optional[Shape]:
        """
        Generate the complete spherical gear with teeth.
        Uses a simplified approach that creates clean, printable geometry.
        """
        try:
            return self._generate_spherical_teeth()
        except Exception as e:
            logging.error(f"Failed to generate spherical gear: {e}")
            # Fallback to simple sphere
            radius_val = self.get_maximum_radius().value()
            return new_shape(Orientation.Front).sphere(radius_val)
