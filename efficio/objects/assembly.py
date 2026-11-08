"""Hierarchical assemblies: place parts, check interference, export a kit.

An :class:`Assembly` is itself an :class:`EfficioObject`, so it can be
rendered on its own, nested inside a larger assembly, and given a
``preview_color`` that every part inside it inherits.
"""

import csv
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

import cadquery as cq

from efficio.objects.base import DEFAULT_PREVIEW_COLOR, Color, EfficioObject
from efficio.objects.fits import Process
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape

Interference = Tuple[str, str, float]
PreviewPart = Tuple[str, cq.Shape, Color]


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
        """Whether the part gets an STL/DXF (stock and bought parts do not)."""
        stock = {Process.ROD_STOCK, Process.DOWEL_STOCK, Process.PURCHASED}
        return not stock.intersection(self.processes)

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
    owner: "Assembly"
    spec: PartSpec

    def preview_color(self, current: Color = DEFAULT_PREVIEW_COLOR) -> Color:
        """The part's own colour, else its assembly's, else ``current``."""
        if self.spec.obj.preview_color is not None:
            return self.spec.obj.preview_color
        return self.owner.resolved_preview_color(current)


class Assembly(EfficioObject):
    """A named group of placed parts and nested sub-assemblies."""

    def __init__(self, name: str, preview_color: Optional[Color] = None):
        self.name = name
        self.preview_color = preview_color
        self.parent = None
        self.parts: Dict[str, PartSpec] = {}
        self.instances: List[PlacedPart] = []
        self.hardware: List[HardwareItem] = []
        self.children: List["Assembly"] = []

    # ------------------------------------------------------------ hierarchy
    def add_subassembly(self, child: "Assembly") -> "Assembly":
        if child is self or any(a is child for a in self._ancestors()):
            raise ValueError("Assembly hierarchy cannot contain cycles")
        if child.parent is not None:
            raise ValueError(f"{child.name} already belongs to an assembly")
        if any(c.name == child.name for c in self.children):
            raise ValueError(f"Duplicate child assembly {child.name!r}")
        child.parent = self
        self.children.append(child)
        return child

    def _ancestors(self) -> Iterator["Assembly"]:
        node = self.parent
        while isinstance(node, Assembly):
            yield node
            node = node.parent

    def group_instances(
        self, name: str, labels: List[str], preview_color: Optional[Color] = None
    ) -> "Assembly":
        """Move direct occurrences into a child without rebuilding or moving solids.

        Part definitions may be shared by children; each occurrence has exactly
        one owner. Hardware is deliberately not copied: its owner must be chosen
        explicitly by the application.
        """
        selected = set(labels)
        if len(selected) != len(labels):
            raise ValueError("Duplicate occurrence labels in grouping")
        direct = {p.label: p for p in self.instances}
        if len(direct) != len(self.instances):
            raise ValueError("Direct occurrence labels must be unique")
        if selected - direct.keys():
            raise ValueError(
                f"Unknown direct occurrences: {sorted(selected - direct.keys())}"
            )
        child = self.add_subassembly(Assembly(name, preview_color))
        for placed in self.instances:
            if placed.label in selected:
                child.register(placed.spec)
                placed.owner = child
                child.instances.append(placed)
        self.instances = [p for p in self.instances if p.label not in selected]
        remaining = {p.part for p in self.instances}
        self.parts = {key: spec for key, spec in self.parts.items() if key in remaining}
        return child

    def walk(self) -> Iterator["Assembly"]:
        """This assembly and every nested sub-assembly, depth first."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, name: str) -> "Assembly":
        matches = [a for a in self.walk() if a.name == name or a.path() == name]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous assembly {name!r}; use its full path")
        raise KeyError(f"no sub-assembly named {name!r} in {self.name}")

    def all_instances(self) -> List[PlacedPart]:
        return [p for a in self.walk() for p in a.instances]

    def all_parts(self) -> Dict[str, PartSpec]:
        merged: Dict[str, PartSpec] = {}
        for assembly in self.walk():
            for name, spec in assembly.parts.items():
                if name in merged and merged[name] is not spec:
                    raise ValueError(f"part name {name!r} is used twice")
                merged[name] = spec
        return merged

    def path(self) -> str:
        names: List[str] = []
        node: Optional[EfficioObject] = self
        while isinstance(node, Assembly):
            names.append(node.name)
            node = node.parent
        return " / ".join(reversed(names))

    def register(self, spec: PartSpec) -> PartSpec:
        if spec.name in self.parts:
            if self.parts[spec.name] is not spec:
                raise ValueError(
                    f"Conflicting part definition {spec.name!r}; reuse its PartSpec"
                )
            return self.parts[spec.name]
        self.parts[spec.name] = spec
        if spec.obj.parent is None:
            spec.obj.parent = self
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
        placed = PlacedPart(label, spec.name, solid, self, spec)
        self.instances.append(placed)
        return placed

    def place_along_x(
        self,
        spec: PartSpec,
        label: str,
        y: float,
        z: float,
        x_from: float,
        toward_positive_x: bool,
        spin: float = 0.0,
    ) -> PlacedPart:
        """Place a part whose axis is local +Z onto a world-X axis.

        ``spin`` is the world angle in the YZ plane (from +Y toward +Z) of the
        part's local +X direction.
        """
        origin = cq.Vector(0, 0, 0)
        solid = self.register(spec).solid()
        if toward_positive_x:
            solid = solid.rotate(origin, cq.Vector(0, 0, 1), spin + 90.0)
            solid = solid.rotate(origin, cq.Vector(0, 1, 0), 90)
        else:
            solid = solid.rotate(origin, cq.Vector(0, 0, 1), 90.0 - spin)
            solid = solid.rotate(origin, cq.Vector(0, 1, 0), -90)
        solid = solid.translate(cq.Vector(x_from, y, z))
        placed = PlacedPart(label, spec.name, solid, self, spec)
        self.instances.append(placed)
        return placed

    def relocate(
        self, rotate_z: float, translation: Tuple[float, float, float]
    ) -> "Assembly":
        """Move a sub-assembly built in its own local frame into place:
        rotate about +Z through the origin, then translate."""
        origin = cq.Vector(0, 0, 0)
        offset = cq.Vector(*translation)
        for placed in self.all_instances():
            solid = placed.solid
            if rotate_z:
                solid = solid.rotate(origin, cq.Vector(0, 0, 1), rotate_z)
            placed.solid = solid.translate(offset)
        return self

    def place_radial(
        self,
        spec: PartSpec,
        label: str,
        x: float,
        y: float,
        z: float,
        angle: float,
    ) -> PlacedPart:
        """Centre a part whose length runs along local +Z across a Y-axis
        shaft at (x, y, z), pointing at ``angle`` in the XZ plane (from +X
        toward +Z), e.g. a cross pin through an axle."""
        origin = cq.Vector(0, 0, 0)
        solid = self.register(spec).solid()
        box = solid.BoundingBox()
        solid = solid.translate(cq.Vector(0, 0, -(box.zmin + box.zmax) / 2))
        solid = solid.rotate(origin, cq.Vector(0, 1, 0), 90)  # local Z -> +X
        solid = solid.rotate(origin, cq.Vector(0, 1, 0), -angle)
        solid = solid.translate(cq.Vector(x, y, z))
        placed = PlacedPart(label, spec.name, solid, self, spec)
        self.instances.append(placed)
        return placed

    def place_world(
        self, spec: PartSpec, label: str, x: float, y: float, z: float
    ) -> PlacedPart:
        solid = self.register(spec).solid().translate(cq.Vector(x, y, z))
        placed = PlacedPart(label, spec.name, solid, self, spec)
        self.instances.append(placed)
        return placed

    def instance(self, label: str) -> PlacedPart:
        matches = [
            p
            for p in self.all_instances()
            if p.label == label or f"{p.owner.path()} / {p.label}" == label
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous occurrence {label!r}; use its full path")
        raise KeyError(f"No occurrence {label!r}")

    def quantities(self) -> Dict[str, int]:
        counts: Dict[str, int] = {name: 0 for name in self.all_parts()}
        for placed in self.all_instances():
            counts[placed.part] += 1
        return counts

    # --------------------------------------------------------- verification
    def interferences(self, tolerance: float = 0.05) -> List[Interference]:
        """Pairs of placed parts (across all sub-assemblies) whose solids
        overlap by more than ``tolerance`` cubic millimetres."""
        instances = self.all_instances()
        boxes = [p.solid.BoundingBox() for p in instances]
        found: List[Interference] = []
        for i, a in enumerate(instances):
            for j in range(i + 1, len(instances)):
                b = instances[j]
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

    # -------------------------------------------------------------- preview
    def compound(self) -> cq.Compound:
        instances = self.all_instances()
        if not instances:
            raise ValueError(f"{self.name} has no parts")
        return cq.Compound.makeCompound([p.solid for p in instances])

    def shape(self) -> Shape:
        result = WorkplaneShape(Orientation.Front)
        result._workplane = cq.Workplane("XY").newObject([self.compound()])
        return result

    def preview_parts(
        self, current: Color = DEFAULT_PREVIEW_COLOR
    ) -> List[PreviewPart]:
        """Every placed solid with its resolved preview colour."""
        return [
            (p.label, p.solid, p.preview_color(current)) for p in self.all_instances()
        ]

    def preview_legend(
        self, current: Color = DEFAULT_PREVIEW_COLOR
    ) -> List[Tuple[str, Color]]:
        """Names and colours of the sub-assemblies (or this assembly alone)."""
        groups = self.children or [self]
        return [(g.name, g.resolved_preview_color(current)) for g in groups]

    # ---------------------------------------------------------------- export
    def bom_rows(self) -> List[Dict[str, str]]:
        """BOM grouped by the sub-assembly that owns each item."""
        rows: List[Dict[str, str]] = []
        for assembly in self.walk():
            quantities = Counter(p.part for p in assembly.instances)
            group = assembly.path()
            for name, spec in assembly.parts.items():
                if not quantities[name]:
                    continue
                rows.append(
                    {
                        "assembly": group,
                        "item": name,
                        "kind": "hardware" if spec.purchased else "fabricated",
                        "quantity": str(quantities[name]),
                        "process": " / ".join(p.value for p in spec.processes),
                        "material": spec.material,
                        "notes": spec.notes,
                    }
                )
            for item in assembly.hardware:
                rows.append(
                    {
                        "assembly": group,
                        "item": item.name,
                        "kind": "hardware",
                        "quantity": str(item.quantity),
                        "process": Process.PURCHASED.value,
                        "material": "",
                        "notes": item.notes,
                    }
                )
        return rows

    def bom_totals(self) -> List[Dict[str, str]]:
        """Procurement roll-up: count each occurrence once across the subtree.

        Keep distinct process/material/notes variants separate. This does not
        infer that differently named catalogue items are interchangeable.
        """
        self.all_parts()  # Reject conflicting identities across children.
        totals: Dict[Tuple[str, ...], Dict[str, str]] = {}
        for row in self.bom_rows():
            key = tuple(
                row[k] for k in ("item", "kind", "process", "material", "notes")
            )
            if key not in totals:
                totals[key] = {**row, "assembly": self.path(), "quantity": "0"}
            totals[key]["quantity"] = str(
                int(totals[key]["quantity"]) + int(row["quantity"])
            )
        return list(totals.values())

    def bom_markdown(self) -> str:
        lines = [f"# {self.name} bill of materials", ""]
        current = None
        for row in self.bom_rows():
            if row["assembly"] != current:
                current = row["assembly"]
                lines += [
                    "",
                    f"## {current}",
                    "",
                    "| Item | Qty | Process | Material | Notes |",
                    "| --- | ---: | --- | --- | --- |",
                ]
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

        for name, spec in self.all_parts().items():
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
