"""Fabrication fits, fastener envelopes and process vocabulary (pure Python)."""

from enum import Enum

# Radial allowances added to holes (subtracted from shafts) in the CAD model.
# They are deliberately small for CNC; FDM users typically add printer-specific
# horizontal expansion compensation in the slicer.
RUNNING_CLEARANCE_MM = 0.20
SLIDING_CLEARANCE_MM = 0.10
PRESS_CLEARANCE_MM = 0.05
BEARING_SEAT_CLEARANCE_MM = 0.05
# Round bores that are pinned/glued to their shaft (e.g. wood dowels, which
# vary by about +/-0.25 mm and are sanded to fit).
PINNED_BORE_CLEARANCE_MM = 0.15
CROSS_PIN_SLOT_CLEARANCE_MM = 0.1


def cross_pin_offset(pin_diameter: float) -> float:
    """Slotted face to pin axis when a cross pin is seated in its slot."""
    return pin_diameter / 2 + CROSS_PIN_SLOT_CLEARANCE_MM


class Process(Enum):
    """How a part is intended to be made."""

    FDM_PRINT = "fdm_print"
    CNC_PLATE = "cnc_plate"  # 2.5D profile cut / etched from plate stock
    ROD_STOCK = "rod_stock"  # cut from ground rod, D-flat filed or ground
    DOWEL_STOCK = "dowel_stock"  # cut from hardwood dowel, cross-drilled
    PURCHASED = "purchased"
    SLIP_CAST = "slip_cast_candidate"
    RESIN_CAST = "resin_cast_candidate"  # tooling/material validation still required


# Pockets that hide a nut or a socket head (sizes come from MetricThread).
NUT_POCKET_CLEARANCE_MM = 0.3
NUT_POCKET_DEPTH_CLEARANCE_MM = 0.2
