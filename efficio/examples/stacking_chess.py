"""The prototype stacking-chess set: one colour of stylized pieces.

Pieces are printed upright and solid, painted, then cast into 38 mm clear
resin cylinders. The 8.3 mm socket in each base takes the locating pin that
centres the piece in the silicone sleeve.
"""

import os
from dataclasses import dataclass
from typing import List

from efficio.objects.games.chess import (
    AbstractStylizedChessPiece,
    StylizedBishop,
    StylizedKing,
    StylizedKnight,
    StylizedPawn,
    StylizedQueen,
    StylizedRook,
)


@dataclass(frozen=True)
class SetEntry:
    name: str
    piece: AbstractStylizedChessPiece
    quantity: int


def stacking_chess_set() -> List[SetEntry]:
    """One colour (16 pieces) of the prototype set at its default dimensions."""
    return [
        SetEntry("pawn", StylizedPawn(), 8),
        SetEntry("rook", StylizedRook(), 2),
        SetEntry("knight", StylizedKnight(), 2),
        SetEntry("bishop", StylizedBishop(), 2),
        SetEntry("queen", StylizedQueen(), 1),
        SetEntry("king", StylizedKing(), 1),
    ]


def export_stacking_chess_stls(directory: str) -> List[str]:
    """Write one STL per piece type (``piece_<name>.stl``); return the paths."""
    os.makedirs(directory, exist_ok=True)
    paths = []
    for entry in stacking_chess_set():
        shape = entry.piece.shape()
        if shape is None:
            raise ValueError(f"{entry.name}: shape() returned None")
        path = os.path.join(directory, f"piece_{entry.name}.stl")
        shape.as_stl_file(path)
        paths.append(path)
    return paths
