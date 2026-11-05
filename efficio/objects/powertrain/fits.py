"""Fabrication fits, fastener envelopes and process vocabulary (pure Python)."""

from enum import Enum

# Radial allowances added to holes (subtracted from shafts) in the CAD model.
# They are deliberately small for CNC; FDM users typically add printer-specific
# horizontal expansion compensation in the slicer.
RUNNING_CLEARANCE_MM = 0.20
SLIDING_CLEARANCE_MM = 0.10
PRESS_CLEARANCE_MM = 0.05
BEARING_SEAT_CLEARANCE_MM = 0.05


class Process(Enum):
    """How a part is intended to be made."""

    FDM_PRINT = "fdm_print"
    CNC_PLATE = "cnc_plate"  # 2.5D profile cut / etched from plate stock
    ROD_STOCK = "rod_stock"  # cut from ground rod, D-flat filed or ground
    PURCHASED = "purchased"


# ISO 4762 M3 socket head / ISO 4032 nut envelopes.
M3_CLEARANCE_RADIUS_MM = 1.7
M3_TAP_RADIUS_MM = 1.25
M3_HEAD_RADIUS_MM = 2.75
M3_HEAD_HEIGHT_MM = 3.0
M3_NUT_ACROSS_CORNERS_MM = 6.35
M3_NUT_HEIGHT_MM = 2.4
M3_NUT_POCKET_ACROSS_CORNERS_MM = M3_NUT_ACROSS_CORNERS_MM + 0.3
M3_NUT_POCKET_DEPTH_MM = 3.2
