"""Hardwood dowel stock catalogue (pure Python).

Sizes follow the Waddell round hardwood dowels stocked at Ace Hardware
(1/8 in to 1 in diameter, 36 in and 48 in lengths).  Ace item numbers are
recorded where known so the BOM can point at a shelf item.  Wood dowels vary
by roughly +/-0.25 mm and swell with humidity, so interfaces that grip a dowel
are drilled or reamed to fit, and drive is taken through a cross pin.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

INCH_MM = 25.4
DOWEL_DIAMETER_TOLERANCE_MM = 0.25


@dataclass(frozen=True)
class WoodDowel:
    nominal: str
    diameter: float
    stock_lengths: tuple[float, ...] = (36 * INCH_MM, 48 * INCH_MM)
    ace_item: str = ""
    manufacturer_part: str = ""

    def description(self) -> str:
        text = f'{self.nominal}" hardwood dowel (Waddell)'
        if self.ace_item:
            text += f", Ace item {self.ace_item}"
        return text

    def stock_pieces(self, cut_lengths: List[float], kerf: float = 3.0) -> int:
        """36 in sticks needed for the given cut lengths (first-fit decreasing)."""
        stick = self.stock_lengths[0]
        remaining: List[float] = []
        for length in sorted(cut_lengths, reverse=True):
            if length > stick:
                raise ValueError(f"{length:.0f} mm cut exceeds a {stick:.0f} mm dowel")
            for i, space in enumerate(remaining):
                if space >= length:
                    remaining[i] = space - length - kerf
                    break
            else:
                remaining.append(stick - length - kerf)
        return len(remaining)


def _inch(numerator: int, denominator: int) -> float:
    return INCH_MM * numerator / denominator


class StandardDowel(Enum):
    D_1_8 = WoodDowel("1/8", _inch(1, 8))
    D_3_16 = WoodDowel(
        "3/16", _inch(3, 16), ace_item="5980503", manufacturer_part="6303UB"
    )
    D_1_4 = WoodDowel(
        "1/4", _inch(1, 4), ace_item="5980552", manufacturer_part="6304UB"
    )
    D_5_16 = WoodDowel(
        "5/16", _inch(5, 16), ace_item="5980420", manufacturer_part="6305UB"
    )
    D_3_8 = WoodDowel(
        "3/8", _inch(3, 8), ace_item="5981139", manufacturer_part="6306UB"
    )
    D_7_16 = WoodDowel("7/16", _inch(7, 16))
    D_1_2 = WoodDowel("1/2", _inch(1, 2))
    D_5_8 = WoodDowel(
        "5/8", _inch(5, 8), ace_item="5981949", manufacturer_part="6310UB"
    )
    D_3_4 = WoodDowel("3/4", _inch(3, 4))
    D_7_8 = WoodDowel("7/8", _inch(7, 8))
    D_1 = WoodDowel("1", _inch(1, 1))

    @property
    def spec(self) -> WoodDowel:
        value: WoodDowel = self.value
        return value

    @staticmethod
    def examples() -> List[str]:
        return ["D_1_4", "D_5_16", "D_3_8"]
