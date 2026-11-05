"""Place parts in a world frame, check interference, export a fabrication kit."""

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import Process
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape

Interference = Tuple[str, str, float]


@dataclass
class PartSpec:
    """A distinct part to fabricate (may be instanced several times)."""

    name: str
    obj: EfficioObject
    processes: Tuple[Process, ...]
    material: str
    notes: str = ""
    _solid: Optional[cq.Shape] = field(default=None, repr=False)

    def solid(self) -> cq.Shape:
        if self._solid is None:
            shape = self.obj.shape()
            if shape is None:
                raise ValueError(f"{self.name} produced no geometry")
            values = [v for v in shape.workplane().vals() if isinstance(v, cq.Shape)]
            if not values:
                raise ValueError(f"{self.name} produced no solids")
            self._solid = (
                values[0] if len(values) == 1 else cq.Compound.makeCompound(values)
            )
        return self._solid

    @property
    def cnc_profile(self) -> bool:
        return Process.CNC_PLATE in self.processes

    @property
    def purchased(self) -> bool:
        """Bought-in parts are modelled for fit checks but not fabricated."""
        return Process.PURCHASED in self.processes

    @property
    def fabricated_file(self) -> bool:
        return not self.purchased and Process.ROD_STOCK not in self.processes

    def shape(self) -> Shape:
        result = WorkplaneShape(Orientation.Front)
        result._workplane = cq.Workplane("XY").newObject([self.solid()])
        return result


@dataclass(frozen=True)
class HardwareItem:
    name: str
    quantity: int
    notes: str = ""


@dataclass
class PlacedPart:
    label: str
    part: str
    solid: cq.Shape


class Assembly:
    def __init__(self, name: str):
        self.name = name
        self.parts: Dict[str, PartSpec] = {}
        self.instances: List[PlacedPart] = []
        self.hardware: List[HardwareItem] = []

    def register(self, spec: PartSpec) -> PartSpec:
        if spec.name in self.parts:
            return self.parts[spec.name]
        self.parts[spec.name] = spec
        return spec

    def add_hardware(self, name: str, quantity: int, notes: str = "") -> None:
        self.hardware.append(HardwareItem(name, quantity, notes))

    # ----------------------------------------------------------- placements
    def place_axial(
        self,
        spec: PartSpec,
        label: str,
        x: float,
        z: float,
        y_from: float,
        toward_positive_y: bool,
        spin: float = 0.0,
    ) -> PlacedPart:
        """Place a part whose rotation axis is local +Z onto a world-Y axis.

        Local z = 0 lands on ``y = y_from`` and local +Z points to +Y or -Y.
        ``spin`` is the world rotation in the XZ plane (from +X toward +Z) of
        the part's local +X direction.
        """
        origin = cq.Vector(0, 0, 0)
        solid = self.register(spec).solid()
        if toward_positive_y:
            solid = solid.rotate(origin, cq.Vector(0, 0, 1), -spin)
            solid = solid.rotate(origin, cq.Vector(1, 0, 0), -90)
        else:
            solid = solid.rotate(origin, cq.Vector(0, 0, 1), spin)
            solid = solid.rotate(origin, cq.Vector(1, 0, 0), 90)
        solid = solid.translate(cq.Vector(x, y_from, z))
        placed = PlacedPart(label, spec.name, solid)
        self.instances.append(placed)
        return placed

    def place_world(
        self, spec: PartSpec, label: str, x: float, y: float, z: float
    ) -> PlacedPart:
        solid = self.register(spec).solid().translate(cq.Vector(x, y, z))
        placed = PlacedPart(label, spec.name, solid)
        self.instances.append(placed)
        return placed

    def instance(self, label: str) -> PlacedPart:
        return next(p for p in self.instances if p.label == label)

    def quantities(self) -> Dict[str, int]:
        counts: Dict[str, int] = {name: 0 for name in self.parts}
        for placed in self.instances:
            counts[placed.part] += 1
        return counts

    # --------------------------------------------------------- verification
    def interferences(self, tolerance: float = 0.05) -> List[Interference]:
        """Pairs of placed parts whose solids overlap by more than ``tolerance``
        cubic millimetres."""
        boxes = [p.solid.BoundingBox() for p in self.instances]
        found: List[Interference] = []
        for i, a in enumerate(self.instances):
            for j in range(i + 1, len(self.instances)):
                b = self.instances[j]
                ba, bb = boxes[i], boxes[j]
                if (
                    ba.xmax <= bb.xmin
                    or bb.xmax <= ba.xmin
                    or ba.ymax <= bb.ymin
                    or bb.ymax <= ba.ymin
                    or ba.zmax <= bb.zmin
                    or bb.zmax <= ba.zmin
                ):
                    continue
                volume = a.solid.intersect(b.solid).Volume()
                if volume > tolerance:
                    found.append((a.label, b.label, volume))
        return found

    def compound(self) -> cq.Compound:
        return cq.Compound.makeCompound([p.solid for p in self.instances])

    def shape(self) -> Shape:
        result = WorkplaneShape(Orientation.Front)
        result._workplane = cq.Workplane("XY").newObject([self.compound()])
        return result

    # ---------------------------------------------------------------- export
    def bom_rows(self) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        quantities = self.quantities()
        for name, spec in self.parts.items():
            rows.append(
                {
                    "item": name,
                    "kind": "hardware" if spec.purchased else "fabricated",
                    "quantity": str(quantities[name]),
                    "process": " / ".join(p.value for p in spec.processes),
                    "material": spec.material,
                    "notes": spec.notes,
                }
            )
        for item in self.hardware:
            rows.append(
                {
                    "item": item.name,
                    "kind": "hardware",
                    "quantity": str(item.quantity),
                    "process": Process.PURCHASED.value,
                    "material": "",
                    "notes": item.notes,
                }
            )
        return rows

    def bom_markdown(self) -> str:
        lines = [
            f"# {self.name} bill of materials",
            "",
            "| Item | Qty | Process | Material | Notes |",
            "| --- | ---: | --- | --- | --- |",
        ]
        for row in self.bom_rows():
            lines.append(
                f"| {row['item']} | {row['quantity']} | {row['process']} | "
                f"{row['material']} | {row['notes']} |"
            )
        return "\n".join(lines) + "\n"

    def export(self, directory: str, include_assembly: bool = True) -> List[str]:
        """Write per-part STL, CNC DXF profiles, BOM and the assembled STL."""
        written: List[str] = []
        parts_dir = os.path.join(directory, "parts")
        cnc_dir = os.path.join(directory, "cnc")
        os.makedirs(parts_dir, exist_ok=True)
        os.makedirs(cnc_dir, exist_ok=True)

        for name, spec in self.parts.items():
            if not spec.fabricated_file:
                continue
            path = os.path.join(parts_dir, f"{name}.stl")
            spec.shape().as_stl_file(path)
            written.append(path)
            if spec.cnc_profile:
                written.append(self._export_dxf(spec, cnc_dir))

        bom_md = os.path.join(directory, "BOM.md")
        with open(bom_md, "w", encoding="utf-8") as handle:
            handle.write(self.bom_markdown())
        written.append(bom_md)

        bom_csv = os.path.join(directory, "bom.csv")
        rows = self.bom_rows()
        with open(bom_csv, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        written.append(bom_csv)

        if include_assembly:
            path = os.path.join(directory, "assembly.stl")
            self.shape().as_stl_file(path)
            written.append(path)
        return written

    @staticmethod
    def _export_dxf(spec: PartSpec, directory: str) -> str:
        solid = spec.solid()
        box = solid.BoundingBox()
        height = (box.zmin + box.zmax) / 2.0
        section = cq.Workplane("XY").newObject([solid]).section(height)
        path = os.path.join(directory, f"{spec.name}.dxf")
        cq.exporters.export(section, path, exportType="DXF")
        return path
