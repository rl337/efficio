from typing import Optional

from efficio.measures import (
    Measure,
    Millimeter
)

from efficio.objects.base import EfficioObject
from efficio.objects.shapes import new_shape, Orientation, Shape
from efficio.objects.primitives import Cylinder


M3_BOLT_CLEARANCE_MILLIMETERS = Millimeter(0.20)
M3_SHAFT_RADIUS_MILLIMETERS = Millimeter(3.0/2.0)
M3_HEAD_HEIGHT_MILLIMETERS = Millimeter(3.0)
M3_HEAD_RADIUS_MILLIMETERS = Millimeter(5.5/2)
M3_NUT_WAF_MILLIMETERS = Millimeter(5.5)
M3_NUT_WAC_MILLIMETERS = Millimeter(6.35)
M3_NUT_HEIGHT_MILLIMETERS = Millimeter(2.4)
M3_CHANNEL_PADDING_MILLIMETERS = Millimeter(0.5)


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

class M3BoltChannel(EfficioObject):
    bolt_assembly: M3BoltAssembly
    column: Cylinder

    def __init__(self, length: Measure):
        self.bolt_assembly = M3BoltAssembly(length, True)
        
        bolt_assembly_bounds = self.bolt_assembly.shape().bounds()
        assembly_width = bolt_assembly_bounds[3] - bolt_assembly_bounds[0]
        assembly_length = bolt_assembly_bounds[4] - bolt_assembly_bounds[1]
        assembly_height = bolt_assembly_bounds[5] - bolt_assembly_bounds[2]
        max_diameter = assembly_width
        if assembly_length > max_diameter:
            max_diameter = assembly_length
        
        self.column = Cylinder(
            Millimeter(assembly_height),
            Millimeter(max_diameter/2 + M3_CHANNEL_PADDING_MILLIMETERS.value())
        )

    def shape(self) -> Optional[Shape]:
        channel = self.column.shape()
        assembly = self.bolt_assembly.shape()
        return channel.cut(assembly)

    def cut(self) -> Optional[Shape]:
        return self.column.shape()
