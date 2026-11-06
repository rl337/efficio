import math
import os
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from efficio.machines import PRUSA_MK4, BuildVolume, PrinterProfile
from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners import BoltAssembly, MetricThread
from efficio.objects.shapes import Orientation, Shape, new_shape


class MoldPolarity(Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


class CottlePurpose(Enum):
    POUR_CONTAINMENT = "pour_containment"
    MOLD_SUPPORT = "mold_support"
    BOTH = "both"


class SplitKind(Enum):
    """Functional mold parting vs printer-fit manufacturing subdivision."""

    FUNCTIONAL = "functional"
    MANUFACTURING = "manufacturing"


@dataclass(frozen=True)
class MoldFeatures:
    """Sizes of the pour, vent, registration and fastening features.

    Defaults suit small resin and plaster casts on a desktop printer.

    ``channel_depth_fraction`` is deprecated and ignored when supplied. Ports
    now reach the master minimum Z so shallow fractions cannot leave them in
    the silicone padding. The field remains accepted for source compatibility;
    supplying a legacy value emits DeprecationWarning when tooling is created.
    """

    registration_pin_radius: float = 1.0
    registration_pin_length: float = 4.0
    sprue_radius: float = 4.0
    vent_radius: float = 2.0
    vent_offset: float = 12.0  # sprue to vent, capped by master Y span
    channel_depth_fraction: Optional[float] = None  # deprecated compatibility field
    registration_offset_fraction: float = 0.25  # pins from the centre
    fastener_offset_fraction: float = 0.3  # cottle bolts from the centre
    fastener: MetricThread = MetricThread.M3
    fastener_boss_wall: float = 2.0
    registration_clearance: float = 0.2


@dataclass
class ToolingSection:
    name: str
    geometry: Shape
    split_kind: SplitKind = SplitKind.FUNCTIONAL

    def dimensions(self) -> Tuple[float, float, float]:
        bounds = self.geometry.bounds()
        if bounds is None:
            raise ValueError(f"{self.name} has no geometry")
        return (
            bounds[3] - bounds[0],
            bounds[4] - bounds[1],
            bounds[5] - bounds[2],
        )

    def fits(self, printer: PrinterProfile) -> bool:
        return printer.build_volume.fits(self.dimensions())


class MoldTooling(EfficioObject):
    """Silicone molds and reusable rigid cottles for casting workflows.

    Master geometry, mold polarity, silicone, and cottle sections remain distinct
    artifacts. Cottle halves are a functional parting split for assembly; if a
    section cannot fit the printer, validate_for_printer raises so a later
    manufacturing subdivision can be introduced explicitly.

    These are geometry prototypes, not production-ready casting tools. Silicone
    parting/release cuts, plaster mother-mold sections and fixtures, sealing,
    print orientation and physical casting validation remain to be designed.
    Positive output is an exact master replica; it is not a complete plaster
    mold. Its envelope clearance represents plaster volume, not silicone.
    The cottle alone does not suspend or position this positive intermediate.
    Pour ports currently use bounds-based placement and require master-specific
    intersection checks for concave/hollow profiles.
    """

    def __init__(
        self,
        master: EfficioObject,
        polarity: MoldPolarity,
        silicone_thickness: Measure = Millimeter(8),
        cottle_wall: Measure = Millimeter(4),
        printer: PrinterProfile = PRUSA_MK4,
        purpose: CottlePurpose = CottlePurpose.BOTH,
        features: MoldFeatures = MoldFeatures(),
    ):
        positive_dimensions = (
            silicone_thickness.value(),
            cottle_wall.value(),
            features.registration_pin_radius,
            features.registration_pin_length,
            features.sprue_radius,
            features.vent_radius,
            features.fastener_boss_wall,
        )
        if any(not math.isfinite(value) or value <= 0 for value in positive_dimensions):
            raise ValueError("Dimensions must be finite and positive")
        for value in (features.registration_clearance, features.vent_offset):
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    "Clearance and vent offset must be finite and nonnegative"
                )
        for value in (
            features.registration_offset_fraction,
            features.fastener_offset_fraction,
        ):
            if not math.isfinite(value) or not 0 < value < 0.5:
                raise ValueError(
                    "Feature offset fractions must be finite and between 0 and 0.5"
                )
        if features.channel_depth_fraction is not None and (
            not math.isfinite(features.channel_depth_fraction)
            or not 0 < features.channel_depth_fraction <= 1
        ):
            raise ValueError(
                "Legacy channel_depth_fraction must be finite and in (0, 1]"
            )
        socket_width = 2 * (
            features.registration_pin_radius + features.registration_clearance
        )
        if socket_width >= cottle_wall.value():
            raise ValueError("Registration socket must fit strictly within cottle wall")
        if features.channel_depth_fraction is not None:
            warnings.warn(
                "channel_depth_fraction is deprecated and ignored; pour ports "
                "reach the master minimum Z",
                DeprecationWarning,
                stacklevel=2,
            )
        self.master = master
        self.polarity = polarity
        self.silicone_thickness = silicone_thickness
        self.cottle_wall = cottle_wall
        self.printer = printer
        self.purpose = purpose
        self.features = features

    def _has_pour_features(self) -> bool:
        return self.purpose in (
            CottlePurpose.POUR_CONTAINMENT,
            CottlePurpose.BOTH,
        )

    def _master_shape_and_bounds(
        self,
    ) -> Tuple[Shape, Tuple[float, float, float, float, float, float]]:
        master_shape = self.master.shape()
        if master_shape is None:
            raise ValueError("Master produced no geometry")
        bounds = master_shape.bounds()
        if bounds is None:
            raise ValueError("Master produced geometry without bounds")
        return master_shape, bounds

    def _silicone_envelope(
        self, bounds: Tuple[float, float, float, float, float, float]
    ) -> Tuple[Shape, Tuple[float, float, float], Tuple[float, float, float]]:
        pad = self.silicone_thickness.value()
        width = bounds[3] - bounds[0] + 2 * pad
        length = bounds[4] - bounds[1] + 2 * pad
        depth = bounds[5] - bounds[2] + 2 * pad
        center = (
            (bounds[0] + bounds[3]) / 2,
            (bounds[1] + bounds[4]) / 2,
            (bounds[2] + bounds[5]) / 2,
        )
        block = (
            new_shape(Orientation.Front).box(width, length, depth).translate(*center)
        )
        return block, (width, length, depth), center

    def _apply_pour_vents(
        self,
        body: Shape,
        center: Tuple[float, float, float],
        depth: float,
    ) -> Shape:
        """Cut sprue and vent channels from the top into the silicone body."""
        if not self._has_pour_features():
            return body

        _, bounds = self._master_shape_and_bounds()
        top_z = center[2] + depth / 2
        # Reach the full master depth, never stop in the padding above it.
        bottom_z = bounds[2]
        for x, y, radius in self._pour_ports(bounds):
            channel = (
                new_shape(Orientation.Front)
                .circle(radius)
                .extrude(top_z - bottom_z)
                .translate(x, y, bottom_z)
            )
            body = body.cut(channel)
        return body

    def _pour_ports(
        self, bounds: Tuple[float, float, float, float, float, float]
    ) -> List[Tuple[float, float, float]]:
        """Global port axes shared by silicone and cottle, within master bounds.

        Bounds alone cannot guarantee vent connectivity for arbitrary hollow or
        concave masters. Verify cavity intersections for each new master.
        """
        x = (bounds[0] + bounds[3]) / 2
        y = (bounds[1] + bounds[4]) / 2
        offset = min(self.features.vent_offset, (bounds[4] - bounds[1]) / 4)
        return [
            (x, y, self.features.sprue_radius),
            (x, y + offset, self.features.vent_radius),
        ]

    def silicone_shape(self) -> Shape:
        master, bounds = self._master_shape_and_bounds()
        block, (_width, _length, depth), center = self._silicone_envelope(bounds)

        if self.polarity is MoldPolarity.NEGATIVE:
            silicone = block.cut(master)
        else:
            # Preserve the complete positive profile. The envelope clearance
            # is space for later plaster, not material to union to this pattern.
            return master

        return self._apply_pour_vents(silicone, center, depth)

    def _cottle_dimensions(
        self,
    ) -> Tuple[float, float, float, Tuple[float, float, float]]:
        _, bounds = self._master_shape_and_bounds()
        pad = self.silicone_thickness.value()
        wall = self.cottle_wall.value()
        width = bounds[3] - bounds[0] + 2 * (pad + wall)
        length = bounds[4] - bounds[1] + 2 * (pad + wall)
        depth = bounds[5] - bounds[2] + 2 * (pad + wall)
        center = (
            (bounds[0] + bounds[3]) / 2,
            (bounds[1] + bounds[4]) / 2,
            (bounds[2] + bounds[5]) / 2,
        )
        return width, length, depth, center

    def _registration_pin_centers(
        self, center: Tuple[float, float, float], length: float, depth: float
    ) -> List[Tuple[float, float, float]]:
        y_offset = length / 2 - self.cottle_wall.value() / 2
        z_offset = depth * self.features.registration_offset_fraction
        return [
            (center[0], center[1] + y_offset, center[2] + z_offset),
            (center[0], center[1] - y_offset, center[2] - z_offset),
        ]

    def _fastener_cutter(self, width: float) -> Shape:
        """Actual shank/head/nut envelope, not its supporting column."""
        spec = self.features.fastener.spec
        cutter = BoltAssembly(
            self.features.fastener, Millimeter(width - spec.head_height), True
        ).shape()
        if cutter is None:
            raise ValueError("bolt assembly produced no geometry")
        return cutter

    def cottle_sections(self) -> List[ToolingSection]:
        """Return two functional clamshell sections with registration and bolts."""
        width, length, depth, center = self._cottle_dimensions()
        wall = self.cottle_wall.value()
        half_width = width / 2
        pin_centers = self._registration_pin_centers(center, length, depth)
        socket_radius = (
            self.features.registration_pin_radius + self.features.registration_clearance
        )
        socket_half_length = (
            self.features.registration_pin_length / 2
            + self.features.registration_clearance
        )
        if socket_half_length >= half_width - wall:
            raise ValueError("Registration socket is too long for cottle section")
        if (
            abs(depth * self.features.registration_offset_fraction) + socket_radius
            >= depth / 2 - wall
        ):
            raise ValueError("Registration socket must stay below the open cottle rim")

        # Pour containment leaves the cottle open at the top; support/both keep
        # a full enclosure (both still gets pour holes cut through the top).
        open_top = self.purpose is CottlePurpose.POUR_CONTAINMENT
        outer_depth = depth if not open_top else depth - wall
        outer_z = center[2] if not open_top else center[2] - wall / 2

        sections: List[ToolingSection] = []
        for index, sign in enumerate((-1, 1)):
            x_center = center[0] + sign * (width / 4)
            shell = (
                new_shape(Orientation.Front)
                .box(half_width, length, outer_depth)
                .translate(x_center, center[1], outer_z)
            )

            # One shared cavity reaches the split plane on both halves.
            # Per-half offset cavities leave walls colliding with silicone.
            cavity = (
                new_shape(Orientation.Front)
                .box(width - 2 * wall, length - 2 * wall, depth - 2 * wall)
                .translate(*center)
            )
            shell = shell.cut(cavity)

            # Bosses remain outside the silicone envelope. Their material
            # supports the head and hex nut seats instead of removing an entire
            # oversized column through the thin enclosure walls.
            spec = self.features.fastener.spec
            boss_radius = max(spec.head_diameter, spec.nut_across_corners) / 2
            boss_radius += self.features.fastener_boss_wall
            boss_y = center[1] + length / 2 + boss_radius - wall / 2
            offset = depth * self.features.fastener_offset_fraction
            for z_offset in (-offset, offset):
                boss = (
                    new_shape(Orientation.Front)
                    .circle(boss_radius)
                    .extrude(half_width)
                    .rotate(0, 90, 0)
                    .translate(
                        center[0] + (-half_width if sign < 0 else 0),
                        boss_y,
                        center[2] + z_offset,
                    )
                )
                shell = shell.union(boss)
                cutter = self._fastener_cutter(width)
                cutter = cutter.rotate(0, 90, 0).translate(
                    center[0] - width / 2, boss_y, center[2] + z_offset
                )
                shell = shell.cut(cutter)

            # Registration: pins on A (sign < 0), sockets on B (sign > 0).
            for pin_x, pin_y, pin_z in pin_centers:
                pin = (
                    new_shape(Orientation.Front)
                    .box(
                        self.features.registration_pin_length,
                        self.features.registration_pin_radius * 2,
                        self.features.registration_pin_radius * 2,
                    )
                    .translate(pin_x, pin_y, pin_z)
                )
                if sign < 0:
                    shell = shell.union(pin)
                else:
                    clearance = self.features.registration_clearance
                    socket = (
                        new_shape(Orientation.Front)
                        .box(
                            self.features.registration_pin_length + 2 * clearance,
                            self.features.registration_pin_radius * 2 + 2 * clearance,
                            self.features.registration_pin_radius * 2 + 2 * clearance,
                        )
                        .translate(pin_x, pin_y, pin_z)
                    )
                    shell = shell.cut(socket)

            if self._has_pour_features() and not open_top:
                # Matching pour/vent openings through the closed cottle roof.
                top_z = center[2] + depth / 2
                roof_cut_height = wall * 2
                _, bounds = self._master_shape_and_bounds()
                for x, y, radius in self._pour_ports(bounds):
                    opening = (
                        new_shape(Orientation.Front)
                        .circle(radius)
                        .extrude(roof_cut_height)
                        .translate(x, y, top_z - roof_cut_height)
                    )
                    shell = shell.cut(opening)

            sections.append(
                ToolingSection(
                    name=chr(ord("A") + index),
                    geometry=shell,
                    split_kind=SplitKind.FUNCTIONAL,
                )
            )

        return sections

    def validate_for_printer(self) -> None:
        oversized = [
            section.name
            for section in self.cottle_sections()
            if not section.fits(self.printer)
        ]
        if oversized:
            raise ValueError(
                f"Tooling sections {oversized} do not fit {self.printer.name}; "
                "manufacturing subdivision is required"
            )

    def export_stl_set(self, directory: str) -> List[str]:
        """Write silicone and all cottle section STLs; return written paths."""
        os.makedirs(directory, exist_ok=True)
        paths: List[str] = []

        silicone_path = os.path.join(directory, "silicone.stl")
        self.silicone_shape().as_stl_file(silicone_path)
        paths.append(silicone_path)

        for section in self.cottle_sections():
            path = os.path.join(directory, f"cottle-{section.name}.stl")
            section.geometry.as_stl_file(path)
            paths.append(path)

        return paths

    def shape(self) -> Optional[Shape]:
        return self.silicone_shape()
