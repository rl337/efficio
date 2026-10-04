from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.m3 import M3BoltChannel
from efficio.objects.shapes import Orientation, Shape, new_shape


class MoldPolarity(Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


class CottlePurpose(Enum):
    POUR_CONTAINMENT = "pour_containment"
    MOLD_SUPPORT = "mold_support"
    BOTH = "both"


@dataclass(frozen=True)
class BuildVolume:
    x: Measure
    y: Measure
    z: Measure

    def fits(self, dimensions: Tuple[float, float, float]) -> bool:
        limits = sorted((self.x.value(), self.y.value(), self.z.value()))
        candidate = sorted(dimensions)
        return all(size <= limit for size, limit in zip(candidate, limits))


@dataclass(frozen=True)
class PrinterProfile:
    name: str
    build_volume: BuildVolume


PRUSA_MK4 = PrinterProfile(
    name="Original Prusa MK4",
    build_volume=BuildVolume(Millimeter(250), Millimeter(210), Millimeter(220)),
)


@dataclass
class ToolingSection:
    name: str
    geometry: Shape

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
    """A first vertical slice for silicone molds and reusable rigid cottles.

    The mold block and cottle are deliberately separate artifacts.  The cottle
    is split for printing/assembly; the silicone block carries the functional
    negative when polarity is NEGATIVE.
    """

    def __init__(
        self,
        master: EfficioObject,
        polarity: MoldPolarity,
        silicone_thickness: Measure = Millimeter(8),
        cottle_wall: Measure = Millimeter(4),
        printer: PrinterProfile = PRUSA_MK4,
        purpose: CottlePurpose = CottlePurpose.BOTH,
    ):
        self.master = master
        self.polarity = polarity
        self.silicone_thickness = silicone_thickness
        self.cottle_wall = cottle_wall
        self.printer = printer
        self.purpose = purpose

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

    def silicone_shape(self) -> Shape:
        master, bounds = self._master_shape_and_bounds()
        pad = self.silicone_thickness.value()
        width = bounds[3] - bounds[0] + 2 * pad
        length = bounds[4] - bounds[1] + 2 * pad
        depth = bounds[5] - bounds[2] + 2 * pad
        center = (
            (bounds[0] + bounds[3]) / 2,
            (bounds[1] + bounds[4]) / 2,
            (bounds[2] + bounds[5]) / 2,
        )

        block = new_shape(Orientation.Front).box(width, length, depth).translate(*center)
        if self.polarity is MoldPolarity.NEGATIVE:
            return block.cut(master)

        # A positive silicone intermediate reproduces the master geometry.
        return master

    def _cottle_dimensions(self) -> Tuple[float, float, float, Tuple[float, float, float]]:
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

    def cottle_sections(self) -> List[ToolingSection]:
        """Return two rigid clamshell sections with M3 assembly channels."""
        width, length, depth, center = self._cottle_dimensions()
        wall = self.cottle_wall.value()
        half_width = width / 2

        sections: List[ToolingSection] = []
        for index, sign in enumerate((-1, 1)):
            x_center = center[0] + sign * (width / 4)
            shell = new_shape(Orientation.Front).box(half_width, length, depth).translate(
                x_center, center[1], center[2]
            )

            inner_width = max(half_width - wall, wall)
            inner_length = max(length - 2 * wall, wall)
            inner_depth = max(depth - 2 * wall, wall)
            inner_x = center[0] + sign * (wall + inner_width / 2)
            cavity = (
                new_shape(Orientation.Front)
                .box(inner_width, inner_length, inner_depth)
                .translate(inner_x, center[1], center[2])
            )
            shell = shell.cut(cavity)

            # Two transverse M3 channels make the halves clamp together.  The
            # existing M3 clearance model remains the source of fastener truth.
            for z_offset in (-depth * 0.3, depth * 0.3):
                channel = M3BoltChannel(Millimeter(width)).cut()
                if channel is None:
                    raise ValueError("M3 bolt channel produced no geometry")
                channel = channel.rotate(0, 90, 0).translate(
                    center[0] - width / 2,
                    center[1],
                    center[2] + z_offset,
                )
                shell = shell.cut(channel)

            sections.append(ToolingSection(chr(ord("A") + index), shell))

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

    def shape(self) -> Optional[Shape]:
        return self.silicone_shape()
