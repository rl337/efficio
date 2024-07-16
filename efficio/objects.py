from typing import Optional, Tuple, BinaryIO
from enum import Enum

import cadquery

from efficio.measures import (
    Measure,
    Millimeter
)

class Orientation(Enum):
    Front = 'XY'
    Left = 'YZ'
    Top = 'XZ'

class JoinOrientation(Enum):
    Front = 1
    Back = 2
    Left = 3
    Right = 4 
    Top = 5
    Bottom = 6

class Alignment(Enum):
    Left = 1
    Right = 2
    Center = 3

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

    def as_stl(self, wfp: BinaryIO) -> None:
        raise NotImplementedError('Shape::as_stl()')

    def as_svg(self, wfp: BinaryIO, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None:
        raise NotImplementedError('Shape::as_stl()')

    def as_stl_file(self, filename: str) -> None:
        with open(filename, 'wb') as wfp:
            self.as_stl(wfp)

    def as_svg_file(self, filename: str, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None:
        with open(filename, 'wb') as wfp:
            self.as_svg(wfp, projection)

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

    def as_stl(self, wfp: BinaryIO) -> None:
        cadquery.exporters.exportShape(shape=self._workplane, file=wfp, exportType='STL')

    def as_svg(self, wfp: BinaryIO, projection: Tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None:
        cadquery.exporters.exportShape(shape=self._workplane, file=wfp, exportType='SVG', opt={"projectionDir": projection})


def new_shape(orientation: Orientation = Orientation.Front) -> WorkplaneShape:
    return WorkplaneShape(orientation)
        

class EfficioObject:

    def cut(self) -> Optional[Shape]:
        return None

    def shape(self) -> Optional[Shape]:
        raise NotImplementedError('EfficioObject::shape()')


M3_BOLT_CLEARANCE_MILLIMETERS = Millimeter(0.20)
M3_SHAFT_RADIUS_MILLIMETERS = Millimeter(3.0/2.0)
M3_HEAD_HEIGHT_MILLIMETERS = Millimeter(3.0)
M3_HEAD_RADIUS_MILLIMETERS = Millimeter(5.5/2)
M3_NUT_WAF_MILLIMETERS = Millimeter(5.5)
M3_NUT_WAC_MILLIMETERS = Millimeter(6.35)
M3_NUT_HEIGHT_MILLIMETERS = Millimeter(2.4)


class M3BoltShaft(EfficioObject):
    _length: Measure
    _has_clearance: bool

    def __init__(self, length: Measure, has_clearance: bool):
        self._length = length
        self._has_clearance = has_clearance

    def shape(self) -> Optional[Shape]:
        shaft_length_mm = self._length.value()
        shaft_radius_mm = M3_SHAFT_RADIUS_MILLIMETERS.value()
        shaft_clearance_mm = 0.0
        if self._has_clearance:
            shaft_clearance_mm += M3_BOLT_CLEARANCE_MILLIMETERS.value()

        shaft_shape = new_shape(Orientation.Front).circle(shaft_radius_mm + shaft_clearance_mm).extrude(shaft_length_mm)

        return shaft_shape

    def length(self) -> Measure:
        return self._length
        

class M3BoltHead(EfficioObject):
    _has_clearance: bool

    def __init__(self, has_clearance: bool):
        self._has_clearance = has_clearance

    def shape(self) -> Optional[Shape]:
        head_length_mm = M3_HEAD_HEIGHT_MILLIMETERS.value()
        head_radius_mm = M3_HEAD_RADIUS_MILLIMETERS.value()
        head_clearance_mm = 0.0
        if self._has_clearance:
            head_clearance_mm += M3_BOLT_CLEARANCE_MILLIMETERS.value()

        head_shape = new_shape(Orientation.Front).circle(head_radius_mm + head_clearance_mm).extrude(head_length_mm)
        return head_shape

class M3Bolt(EfficioObject):
    head: M3BoltHead
    shaft: M3BoltShaft
    
    def __init__(self, length: Measure, has_clearance: bool):
        self.head = M3BoltHead(has_clearance)
        self.shaft = M3BoltShaft(length, has_clearance)

    def shape(self) -> Optional[Shape]:
        head_shape = self.head.shape()
        if head_shape is None:
            return None

        shaft_shape = self.shaft.shape()
        if shaft_shape is None:
            return None
        shaft_shape = shaft_shape.translate(0, 0, M3_HEAD_HEIGHT_MILLIMETERS.value())

        return head_shape.union(shaft_shape)


class M3HexNut(EfficioObject):
    _has_clearance: bool

    def __init__(self, has_clearance: bool):
        self._has_clearance = has_clearance
    
    def shape(self) -> Optional[Shape]:
        nut_wac_mm = M3_NUT_WAC_MILLIMETERS.value()
        nut_height_mm = M3_NUT_HEIGHT_MILLIMETERS.value()
        nut_clearance_mm = 0.0
        if self._has_clearance:
            nut_clearance_mm = M3_BOLT_CLEARANCE_MILLIMETERS.value()

        nut_shape = new_shape(Orientation.Front).polygon(6, nut_wac_mm + nut_clearance_mm).extrude(nut_height_mm)
        return nut_shape

class M3BoltAssembly(EfficioObject):
    bolt: M3Bolt
    nut: M3HexNut

    def __init__(self, length: Measure, has_clearance: bool):
        self.bolt = M3Bolt(length, has_clearance)
        self.nut = M3HexNut(has_clearance)
    
    def shape(self) -> Optional[Shape]:
        bolt_shape = self.bolt.shape()
        if bolt_shape is None:
            return None

        nut_shape = self.nut.shape()
        if nut_shape is None:
            return None

        head_height_mm = M3_HEAD_HEIGHT_MILLIMETERS.value()
        shaft_height_mm = self.bolt.shaft.length().value()
        nut_height_mm = M3_NUT_HEIGHT_MILLIMETERS.value()

        nut_shape = nut_shape.translate(0, 0, head_height_mm + shaft_height_mm - nut_height_mm)
        return bolt_shape.union(nut_shape)
