import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import BinaryIO, List, Optional, Tuple, cast

import cadquery
from cadquery import Vector
from cadquery.cq import CQObject  # Added specific import for CQObject


class Orientation(Enum):
    Front = "XY"
    Left = "YZ"
    Top = "XZ"


class Wires:
    _wires: cadquery.Wire

    def __init__(self, wires: cadquery.Wire):
        self._wires = wires

    def val(self) -> cadquery.Wire:
        return self._wires

    def revolve(
        self,
        angle: float,
        point: Tuple[float, float, float],
        axis: Tuple[float, float, float],
    ) -> "Shape":
        face = cadquery.Face.makeFromWires(self._wires)

        # new_shape() returns an instance of Shape, which is an ABC.
        # We need to cast it to WorkplaneShape to access _workplane.
        shape_instance = new_shape(Orientation.Front)
        ws = cast(WorkplaneShape, shape_instance)

        # Perform the revolve operation using the _workplane attribute of WorkplaneShape.
        # For a pending solid (which is what .add(face).toPending() creates),
        # the CadQuery revolve method for sweeping a face uses axisStartPoint and axisEndPoint.
        start_vec = cadquery.Vector(point)
        end_vec = start_vec + cadquery.Vector(
            axis
        )  # axis here is treated as a direction vector from 'point'

        ws._workplane = (
            ws._workplane.add(face)
            .toPending()
            .revolve(
                angleDegrees=angle,
                axisStart=start_vec,  # Changed from axisStartPoint
                axisEnd=end_vec,  # Changed from axisEndPoint
            )
        )
        return ws  # Return the WorkplaneShape instance


class Shape(ABC):

    @abstractmethod
    def workplane(self) -> cadquery.Workplane:
        raise NotImplementedError

    @abstractmethod
    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        raise NotImplementedError

    @abstractmethod
    def box(self, width: float, length: float, depth: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def sphere(self, radius: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def circle(self, radius: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def extrude(self, distance: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def union(self, other: "Shape") -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def cut(self, other: "Shape") -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def translate(self, x: float, y: float, z: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def rotate(self, x: float, y: float, z: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def polygon(self, sides: int, side_length: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def polyline(self, points: List[Tuple[float, float]]) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def close(self) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def revolve(
        self,
        angle: float,
        center_point: Tuple[float, float, float],
        axis_vector: Tuple[float, float, float],
    ) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def fillet_edges(self, radius: float) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def cut_from_top(self, distance_from_top: float, clone: bool = False) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def cut_from_bottom(
        self, distance_from_bottom: float, clone: bool = False
    ) -> "Shape":
        raise NotImplementedError

    @abstractmethod
    def extract_face_from_top(self) -> Wires:  # Keeping Wires as per current structure
        raise NotImplementedError

    @abstractmethod
    def as_stl_file(self, filename: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def as_svg_file(
        self, filename: str, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def isValid(self) -> bool:
        raise NotImplementedError


class WorkplaneShape(Shape):
    _orientation: Orientation
    _workplane: cadquery.Workplane

    def __init__(self, orientation: Orientation):
        self._orientation = orientation
        self._workplane = cadquery.Workplane(self._orientation.value)

    def workplane(self) -> cadquery.Workplane:
        return self._workplane

    def box(self, width: float, length: float, depth: float) -> "Shape":
        self._workplane = self._workplane.box(width, length, depth)
        return self

    def sphere(self, radius: float) -> "Shape":
        self._workplane = self._workplane.sphere(radius)
        return self

    def circle(self, radius: float) -> Shape:
        self._workplane = self._workplane.circle(radius)
        return self

    def extrude(self, distance: float) -> Shape:
        self._workplane = self._workplane.extrude(distance)
        return self

    def union(self, other: Shape) -> Shape:
        if not isinstance(other, self.__class__):
            raise TypeError(f"Unsupported Shape: {type(other).__name__}")

        self._workplane = self._workplane.union(other.workplane())
        return self

    def cut(self, other: Shape) -> Shape:
        if not isinstance(other, self.__class__):
            raise TypeError(f"Unsupported Shape: {type(other).__name__}")

        self._workplane = self._workplane.cut(other.workplane())
        return self

    def translate(self, x: float, y: float, z: float) -> Shape:
        self._workplane = self._workplane.translate((x, y, z))
        return self

    def rotate(self, x: float, y: float, z: float) -> "Shape":
        if x:
            self._workplane = self._workplane.rotate((0, 0, 0), (1, 0, 0), x)
        if y:
            self._workplane = self._workplane.rotate((0, 0, 0), (0, 1, 0), y)
        if z:
            self._workplane = self._workplane.rotate((0, 0, 0), (0, 0, 1), z)

        return self

    def mirror(
        self, mirror_x: bool = False, mirror_y: bool = False, mirror_z: bool = False
    ) -> "Shape":
        if mirror_x:
            self._workplane = self._workplane.mirrorX()
        if mirror_y:
            self._workplane = self._workplane.mirrorY()
        if mirror_z:
            self._workplane = self._workplane.mirror("ZX")
        return self

    def polygon(self, sides: int, side_length: float) -> Shape:
        self._workplane = self._workplane.polygon(sides, side_length)
        return self

    def polyline(self, points: List[Tuple[float, float]]) -> Shape:
        # The current implementation of polyline implicitly closes the shape.
        # If a user wants an open polyline, this would need adjustment,
        # and then close() would be more critical.
        self._workplane = (
            self._workplane.moveTo(points[0][0], points[0][1]).polyline(points).close()
        )
        return self

    def close(self) -> "Shape":
        self._workplane = self._workplane.close()
        return self

    def revolve(
        self,
        angle: float,
        center_point: Tuple[float, float, float],
        axis_vector: Tuple[float, float, float],
    ) -> "Shape":
        # Assuming the workplane has a 2D sketch (wire/face) on its stack to be revolved.
        # CadQuery's Workplane.revolve for sketches uses axisStartPoint and axisEndPoint.
        # center_point is the start of the axis, center_point + axis_vector is the end.
        axis_start = cadquery.Vector(center_point)
        axis_end = axis_start + cadquery.Vector(axis_vector)
        # Corrected keyword arguments as per MyPy's suggestion for Workplane.revolve
        self._workplane = self._workplane.revolve(
            angleDegrees=angle, axisStart=axis_start, axisEnd=axis_end
        )
        return self

    def fillet_edges(self, radius: float) -> "Shape":
        self._workplane = self._workplane.edges().fillet(radius)
        return self

    def cut_from_top(self, distance_from_top: float, clone: bool = False) -> "Shape":
        result = (
            self._workplane.faces(">Z")
            .workplane(-distance_from_top)
            .split(keepTop=True)
        )
        if not clone:
            self._workplane = result
            return self

        cloned = WorkplaneShape(self._orientation)
        cloned._workplane = result
        return cloned

    def cut_from_bottom(
        self, distance_from_bottom: float, clone: bool = False
    ) -> "Shape":
        result = (
            self._workplane.faces("<Z")
            .workplane(-distance_from_bottom)
            .split(keepTop=True)
        )
        if not clone:
            self._workplane = result
            return self

        cloned = WorkplaneShape(self._orientation)
        cloned._workplane = result
        return cloned

    def assert_points_are_planar(
        self, points: List[Tuple[float, float, float]]
    ) -> None:
        if len(points) < 3:
            return

        p0, p1, p2 = points[:3]  # Take first 3 points
        v1 = Vector(p1) - Vector(p0)
        v2 = Vector(p2) - Vector(p0)
        normal = v1.cross(v2)  # Compute the normal vector

        # Check if remaining points satisfy the plane equation
        for p in points[3:]:
            vp = Vector(p) - Vector(p0)
            if abs(normal.dot(vp)) > 1e-6:  # Small tolerance for floating-point errors
                raise AssertionError("Points are not planar")

    def extract_face_from_top(
        self, clip_around_axis: bool = False
    ) -> Wires:  # clip_around_axis is unused
        # .val() should ideally return a single Shape if a unique face is selected.
        # Perform an isinstance check for robustness.
        face_obj = self._workplane.toPending().faces(">Z").val()

        if not isinstance(face_obj, cadquery.Shape):
            raise TypeError(
                f"Expected a cadquery.Shape for the top face, but got {type(face_obj)}"
            )

        # Now face_obj is known to be a cadquery.Shape (specifically, a cq.Face)
        # .wires() returns a WireList. We need a single Wire for the Wires constructor.
        wire_list = face_obj.wires()
        # Get the list of wires from the WireList
        # Type ignore because MyPy doesn't recognize WireList.vals() method
        wire_list_vals = wire_list.vals()  # type: ignore
        if not wire_list_vals:  # Check if the list of wires is empty
            raise ValueError("No wires found on the top face.")

        # Get the first wire from the list
        single_wire_candidate = wire_list_vals[0]

        if isinstance(single_wire_candidate, list) and len(single_wire_candidate) == 1:
            # If .val() returns a list with one wire (some CQ versions/contexts might do this)
            single_wire = single_wire_candidate[0]
        elif isinstance(single_wire_candidate, cadquery.Wire):
            single_wire = single_wire_candidate
        else:
            raise TypeError(
                f"Expected a cadquery.Wire from face.wires().val(), but got {type(single_wire_candidate)}"
            )

        if not isinstance(single_wire, cadquery.Wire):
            # This check is somewhat redundant if the above logic is correct, but belt-and-suspenders.
            raise TypeError(
                f"Extracted object for wire is not a cadquery.Wire, but {type(single_wire)}"
            )

        cleaned_wire = single_wire.clean()  # clean() on a Wire returns a Wire

        return Wires(cleaned_wire)

    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        shapes = self._workplane.vals()

        # Ensure shapes is not None and is a list before checking its length.
        # vals() should return a list, which could be empty.
        if not shapes:  # Handles None or empty list
            return None

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for shape in shapes:
            if not hasattr(shape, "BoundingBox"):
                continue
            bounding_box = shape.BoundingBox()
            min_x = min(min_x, bounding_box.xmin)
            min_y = min(min_y, bounding_box.ymin)
            min_z = min(min_z, bounding_box.zmin)
            max_x = max(max_x, bounding_box.xmax)
            max_y = max(max_y, bounding_box.ymax)
            max_z = max(max_z, bounding_box.zmax)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def as_stl_file(self, filename: str) -> None:
        cadquery.exporters.export(
            self._workplane,
            fname=filename,
            exportType="STL",
            tolerance=0.01,
            angularTolerance=0.1,
        )

    def as_svg_file(
        self, filename: str, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    ) -> None:
        cadquery.exporters.export(
            self._workplane,
            fname=filename,
            exportType="SVG",
            opt={"projectionDir": projection},
        )

    def isValid(self) -> bool:
        # Attempt to get all objects (Solids, Compounds, etc.) from the workplane stack
        try:
            # cadquery.Workplane.vals() returns a list of CQ Shape objects on the stack.
            # Using CQObject as a general type for items that could be on stack,
            # though we are primarily interested in validating cq.Shape items.
            items_on_stack: List[CQObject] = (
                self._workplane.vals()
            )  # Use imported CQObject
        except Exception as e:
            logging.error(f"Error accessing workplane values: {e}")
            return False  # Cannot determine validity if values cannot be accessed

        if not items_on_stack:
            # Whether an empty workplane is "valid" can be debated.
            # For many practical purposes, a shape object with no geometry might be considered invalid
            # or at least not useful. However, for the isValid() method's scope,
            # an empty stack itself isn't necessarily an error state of the Workplane object.
            # Let's consider it valid if it's empty but not in an error state.
            # If subsequent operations require geometry, they will fail.
            logging.debug("Workplane is empty. Considered valid for isValid() context.")
            return True

        for item in items_on_stack:
            if not isinstance(item, cadquery.Shape):
                # If the item on the stack is not a CadQuery Shape (e.g., could be a Vector, Location),
                # we skip direct validation of it as a Shape.
                # The presence of non-Shape items doesn't automatically make the WorkplaneShape invalid,
                # unless the goal is to ensure it *only* contains valid, solid geometry.
                # For now, we only validate items that are supposed to be Shapes.
                logging.debug(
                    f"Skipping validation for non-Shape item on stack: {type(item)}"
                )
                continue

            # At this point, item is a cadquery.Shape
            shape_cq: cadquery.Shape = item

            if shape_cq.isNull():
                logging.debug(f"A CadQuery Shape on stack is null: {shape_cq}")
                return False

            # The .Closed() check is primarily for solids.
            # If the shape is a wire or face, it might not be "Closed" in the solid sense.
            # However, if we expect final shapes to be valid solids, this is a reasonable check.
            if hasattr(shape_cq, "Closed") and not shape_cq.Closed():
                logging.debug(f"Error: CadQuery Shape {shape_cq} is not closed.")
                return False

            # Perform CadQuery's own validity check.
            try:
                if not shape_cq.isValid():
                    logging.debug(
                        f"Error: CadQuery Shape {shape_cq} is not valid (according to shape_cq.isValid())."
                    )
                    # Attempt to clean and re-check as a fallback
                    try:
                        logging.debug(
                            f"Attempting to clean shape {shape_cq} and re-validate."
                        )
                        cleaned_shape = shape_cq.clean()
                        if not cleaned_shape.isValid():
                            logging.debug(
                                f"Error: Shape {shape_cq} is still not valid after cleaning."
                            )
                            return False
                        logging.debug(f"Shape {shape_cq} became valid after cleaning.")
                    except Exception as e_clean:
                        logging.debug(
                            f"Error during shape cleaning or re-validation for {shape_cq}: {e_clean}"
                        )
                        return False  # If cleaning fails or cleaned version is invalid
            except Exception as e_val:
                # This catches errors from shape_cq.isValid() itself, if any.
                logging.debug(
                    f"Error during CadQuery Shape validation for {shape_cq}: {e_val}"
                )
                return False

            # If we've reached here for this shape_cq, it's considered valid.
            logging.debug(f"CadQuery Shape {shape_cq} passed validation checks.")

        # If all cadquery.Shape objects on the stack are valid
        return True


def new_shape(orientation: Orientation = Orientation.Front) -> Shape:
    return WorkplaneShape(orientation)
