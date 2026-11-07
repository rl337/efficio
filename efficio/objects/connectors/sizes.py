"""Named nominal hose IDs, not barb crest diameters or interchangeability claims."""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class HoseSize:
    label: str
    id_mm: float
    od_mm: Optional[float] = None
    source: str = "nominal dimensional selection; OD and service depend on product"
    service: str = "unqualified; select and test an actual hose"

    def __post_init__(self) -> None:
        if not math.isfinite(self.id_mm) or self.id_mm <= 0:
            raise ValueError("hose ID must be positive and finite")
        if self.od_mm is not None and (
            not math.isfinite(self.od_mm) or self.od_mm <= self.id_mm
        ):
            raise ValueError("hose OD must exceed ID")


class CommonHoseSize(Enum):
    METRIC_4_MM_ID = HoseSize("4 mm ID", 4.0)
    METRIC_6_MM_ID = HoseSize("6 mm ID", 6.0)
    METRIC_8_MM_ID = HoseSize("8 mm ID", 8.0)
    METRIC_10_MM_ID = HoseSize("10 mm ID", 10.0)
    METRIC_12_MM_ID = HoseSize("12 mm ID", 12.0)
    # Exact decimal conversions using 25.4 mm per inch; not nearby metric sizes.
    INCH_1_8_ID = HoseSize("1/8 inch nominal ID", 3.175)
    INCH_3_16_ID = HoseSize("3/16 inch nominal ID", 4.7625)
    INCH_1_4_ID = HoseSize("1/4 inch nominal ID", 6.35)
    INCH_5_16_ID = HoseSize("5/16 inch nominal ID", 7.9375)
    INCH_3_8_ID = HoseSize("3/8 inch nominal ID", 9.525)
    INCH_1_2_ID = HoseSize("1/2 inch nominal ID", 12.7)
    DANNER_AIRLINE_3_16_ID = HoseSize(
        "Danner aquarium airline: nominal 3/16 inch ID",
        4.7625,
        None,
        "https://dannermfg.com/products/tubing-check-valves",
        "aquarium airline; water-pump service and fit unqualified",
    )
    TETRA_AH_4_6 = HoseSize(
        "Tetra AH 50-400 aquarium airline: 4 mm ID / 6 mm OD",
        4.0,
        6.0,
        "https://www.tetra.net/en-eu/products/tetra-ah-50-400-air-pump-hose",
        "aquarium airline; not a measured Whisper barb or water-pump qualification",
    )
