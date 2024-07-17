from typing import Optional, Tuple, BinaryIO
from enum import Enum

import cadquery

class Orientation(Enum):
    Front = 'XY'
    Left = 'YZ'
    Top = 'XZ'

class Shape:

    def workplane(self) -> cadquery.Workplane:
        raise NotImplementedError('Shape::workplane()')

    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        raise NotImplementedError('Shape::bounds()')

    def circle(self, radius: float) -> 'Shape':
        raise NotImplementedError('Shape::circle()')
    
    def extrude(self, distance: float) -> 'Shape':
        raise NotImplementedError('Shape::extrude()')

    def union(self, other: 'Shape') -> 'Shape':
        raise NotImplementedError('Shape::union()')

    def translate(self, x: float, y: float, z: float) -> 'Shape':
        raise NotImplementedError('Shape::translate()')

    def polygon(self, sides: int, side_length: float) -> 'Shape':
        raise NotImplementedError('Shape::polygon()')

    def as_stl_file(self, filename: str) -> None:
        raise NotImplementedError('Shape::as_stl_file()')

    def as_svg_file(self, filename: str, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None:
        raise NotImplementedError('Shape::as_svg_file()')

class WorkplaneShape(Shape):
    _orientation: Orientation
    _workplane: cadquery.Workplane

    def __init__(self, orientation: Orientation):
        self._orientation = orientation
        self._workplane = cadquery.Workplane(self._orientation.value)

    def workplane(self) -> cadquery.Workplane:
        return self._workplane

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

    def translate(self, x: float, y: float, z: float) -> Shape:
        self._workplane = self._workplane.translate((x, y, z))
        return self

    def polygon(self, sides: int, side_length: float) -> Shape:
        self._workplane = self._workplane.polygon(sides,  side_length)
        return self

    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        shapes = self._workplane.vals()
        if shapes is None or len(shapes) == 0:
            return None

        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        for shape in shapes:
            if not hasattr(shape, 'BoundingBox'):
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
        cadquery.exporters.export(self._workplane, fname=filename, exportType='STL')

    def as_svg_file(self, filename: str, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None:
        cadquery.exporters.export(self._workplane, fname=filename, exportType='SVG', opt={"projectionDir": projection})


def new_shape(orientation: Orientation = Orientation.Front) -> Shape:
    return WorkplaneShape(orientation)
