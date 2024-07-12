from typing import Optional, Tuple
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
        raise NotImplementedError('Shape::shape()')

    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        raise NotImplementedError('Shape::bounds()')

    def circle(self, radius: float) -> 'Shape':
        raise NotImplementedError('Shape::circle()')
    
    def extrude(self, distance: float) -> 'Shape':
        raise NotImplementedError('Shape::extrude()')

    def union(self, other: 'Shape') -> 'Shape':
        raise NotImplementedError('Shape::union()')


class WorkplaneShape(Shape):
    _orientation: Orientation
    _workplane: cadquery.Workplane

    def __init__(self, orientation: Orientation):
        self._orientation = orientation
        self._workplane = cadquery.Workplane(self._orientation.value)

    def circle(self, radius: float) -> 'WorkplaneShape':
        self._workplane = self._workplane.circle(radius)
        return self
    
    def extrude(self, distance: float) -> 'WorkplaneShape':
        self._workplane = self._workplane.extrude(distance)
        return self

    def union(self, other: Shape) -> 'WorkplaneShape':
        if not isinstance(other, self.__class__):
            raise TypeError(f"Unsupported Shape: {type(other).__name__}")
        
        self._workplane = self._workplane.union(other.workplane())
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


def new_shape(orientation: Orientation = Orientation.Front) -> WorkplaneShape:
    return WorkplaneShape(orientation)
        

class BasicObject:

    def cut(self) -> Optional[Shape]:
        return None

    def shape(self) -> Optional[Shape]:
        raise NotImplementedError('BasicObject::shape()')


M3_BOLT_CLEARANCE_MILLIMETERS = Millimeter(0.25)
M3_SHAFT_RADIUS_MILLIMETERS = Millimeter(3.0/2.0)
M3_HEAD_HEIGHT_MILLIMETERS = Millimeter(3.0)
M3_HEAD_RADIUS_MILLIMETERS = Millimeter(5.5/2)

class M3BoltShaft(BasicObject):
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

        shaft_shape = WorkplaneShape(Orientation.Front).circle(shaft_radius_mm + shaft_clearance_mm).extrude(shaft_length_mm)

        return shaft_shape

class M3BoltHead(BasicObject):
    _has_clearance: bool

    def __init__(self, has_clearance: bool):
        self._has_clearance = has_clearance

    def shape(self) -> Optional[Shape]:
        head_length_mm = M3_HEAD_HEIGHT_MILLIMETERS.value()
        head_radius_mm = M3_SHAFT_RADIUS_MILLIMETERS.value()
        head_clearance_mm = 0.0
        if self._has_clearance:
            head_clearance_mm += M3_BOLT_CLEARANCE_MILLIMETERS.value()

        head_shape = WorkplaneShape(Orientation.Front).circle(head_radius_mm + head_clearance_mm).extrude(head_length_mm)

        return head_shape

class M3Bolt(BasicObject):
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

        return head_shape.union(shaft_shape)

