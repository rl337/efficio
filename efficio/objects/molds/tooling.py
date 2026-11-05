import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from efficio.machines import PRUSA_MK4, BuildVolume, PrinterProfile
from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners import BoltChannel, MetricThread
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
    """

    registration_pin_radius: float = 2.0
    registration_pin_length: float = 4.0
    sprue_radius: float = 4.0
    vent_radius: float = 2.0
    vent_offset: float = 12.0  # sprue to vent, capped by the mold depth
    channel_depth_fraction: float = 0.85  # how far pour channels reach down
    registration_offset_fraction: float = 0.25  # pins from the centre
    fastener_offset_fraction: float = 0.3  # cottle bolts from the centre
    fastener: MetricThread = MetricThread.M3


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

        top_z = center[2] + depth / 2
        # Channels extend from above the block through most of its depth so they
        # reliably open the top and reach the master cavity / positive core.
        channel_height = depth * self.features.channel_depth_fraction
        sprue = (
            new_shape(Orientation.Front)
            .box(
                self.features.sprue_radius * 2,
                self.features.sprue_radius * 2,
                channel_height,
            )
            .translate(center[0], center[1], top_z - channel_height / 2)
        )
        vent = (
            new_shape(Orientation.Front)
            .box(
                self.features.vent_radius * 2,
                self.features.vent_radius * 2,
                channel_height,
            )
            .translate(
                center[0],
                center[1] + min(depth, self.features.vent_offset),
                top_z - channel_height / 2,
            )
        )
        return body.cut(sprue).cut(vent)

    def silicone_shape(self) -> Shape:
        master, bounds = self._master_shape_and_bounds()
        block, (_width, _length, depth), center = self._silicone_envelope(bounds)

        if self.polarity is MoldPolarity.NEGATIVE:
            silicone = block.cut(master)
        else:
            # Positive intermediate: master embedded in a silicone envelope so
            # handling thickness is real material, not a bare master clone.
            silicone = block.union(master)

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
        y_offset = length * self.features.registration_offset_fraction
        z_offset = depth * self.features.registration_offset_fraction
        return [
            (center[0], center[1] + y_offset, center[2] + z_offset),
            (center[0], center[1] - y_offset, center[2] - z_offset),
        ]

    def _fastener_cutter(self, width: float) -> Shape:
        """Clearance column plus bolt/nut assembly envelope for head seats."""
        channel = BoltChannel(self.features.fastener, Millimeter(width))
        cutter = channel.cut()
        if cutter is None:
            raise ValueError("bolt channel produced no cut geometry")

        assembly = channel.bolt_assembly.shape()
        if assembly is not None:
            cutter = cutter.union(assembly)
        return cutter

    def cottle_sections(self) -> List[ToolingSection]:
        """Return two functional clamshell sections with registration and bolts."""
        width, length, depth, center = self._cottle_dimensions()
        wall = self.cottle_wall.value()
        half_width = width / 2
        pin_centers = self._registration_pin_centers(center, length, depth)

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

            inner_width = max(half_width - wall, wall)
            inner_length = max(length - 2 * wall, wall)
            inner_depth = max(outer_depth - (0 if open_top else 2 * wall), wall)
            inner_x = center[0] + sign * (wall + inner_width / 2)
            inner_z = outer_z if open_top else center[2]
            cavity = (
                new_shape(Orientation.Front)
                .box(inner_width, inner_length, inner_depth)
                .translate(inner_x, center[1], inner_z)
            )
            shell = shell.cut(cavity)

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
                    shell = shell.cut(pin)

            # Transverse fasteners (features.fastener) with assembly clearances.
            offset = depth * self.features.fastener_offset_fraction
            for z_offset in (-offset, offset):
                cutter = self._fastener_cutter(width)
                cutter = cutter.rotate(0, 90, 0).translate(
                    center[0] - width / 2,
                    center[1],
                    center[2] + z_offset,
                )
                shell = shell.cut(cutter)

            if self._has_pour_features() and not open_top:
                # Matching pour/vent openings through the closed cottle roof.
                top_z = center[2] + depth / 2
                roof_cut_height = wall * 2
                for y_off, radius in (
                    (0.0, self.features.sprue_radius),
                    (min(depth, self.features.vent_offset), self.features.vent_radius),
                ):
                    opening = (
                        new_shape(Orientation.Front)
                        .box(radius * 2, radius * 2, roof_cut_height)
                        .translate(
                            center[0] + sign * (half_width / 2),
                            center[1] + y_off,
                            top_z - roof_cut_height / 2,
                        )
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
