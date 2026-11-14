"""Stylized stacking-chess pieces: default geometry is pinned to the prototype
set, other parameter sets build, and bad dimensions are rejected."""

import math
from pathlib import Path
from typing import Callable, List, Tuple

import cadquery as cq
import pytest

from efficio.examples.stacking_chess import (
    export_stacking_chess_stls,
    stacking_chess_set,
)
from efficio.objects.games.chess import (
    KNIGHT_OUTLINE,
    AbstractStylizedChessPiece,
    BishopDimensions,
    ChessBodyDimensions,
    KingDimensions,
    KnightDimensions,
    PawnDimensions,
    QueenDimensions,
    RookDimensions,
    StylizedBishop,
    StylizedKing,
    StylizedKnight,
    StylizedPawn,
    StylizedQueen,
    StylizedRook,
)
from efficio.objects.games.chess.geometry import cubic_bezier, quadratic_bezier

# Volume (mm^3) and height (mm) of the prototype set the defaults reproduce.
PROTOTYPE: List[Tuple[Callable[[], AbstractStylizedChessPiece], float, float]] = [
    (StylizedPawn, 13280.9365, 51.8666),
    (StylizedRook, 18689.6193, 58.0),
    (StylizedKnight, 17243.8085, 77.2318),
    (StylizedBishop, 17377.1355, 82.5),
    (StylizedQueen, 18416.7630, 72.0),
    (StylizedKing, 19317.2113, 85.5),
]


def _solid(piece: AbstractStylizedChessPiece) -> cq.Solid:
    solids = piece.solid().solids().vals()
    assert len(solids) == 1
    solid = solids[0]
    assert isinstance(solid, cq.Solid)
    assert solid.isValid()
    return solid


def _volume(piece: AbstractStylizedChessPiece) -> float:
    return _solid(piece).Volume()


@pytest.mark.parametrize(
    "make, volume, height",
    PROTOTYPE,
    ids=[getattr(make, "__name__") for make, _, _ in PROTOTYPE],
)
def test_defaults_reproduce_prototype_set(
    make: Callable[[], AbstractStylizedChessPiece], volume: float, height: float
) -> None:
    piece = make()
    assert _volume(piece) == pytest.approx(volume, abs=0.01)
    shape = piece.shape()
    assert shape is not None
    bounds = shape.bounds()
    assert bounds is not None
    assert bounds[:3] == pytest.approx((-16, -16, 0), abs=1e-4)
    assert bounds[3:] == pytest.approx((16, 16, height), abs=1e-4)
    assert piece.problems() == []


def test_pin_socket_is_a_parameter() -> None:
    solid = StylizedPawn(ChessBodyDimensions(pin_socket_depth=0))
    removed = math.pi * (8.3 / 2) ** 2 * 5.0
    assert _volume(solid) - _volume(StylizedPawn()) == pytest.approx(removed, rel=1e-4)


def test_rook_single_crenel_keeps_the_other_slot() -> None:
    single = StylizedRook(dimensions=RookDimensions(cross_crenels=False))
    # Filling one slot adds its length outside the other slot: 8 x 14 x 5.5.
    assert _volume(single) - _volume(StylizedRook()) == pytest.approx(616, rel=1e-3)


def test_bishop_slit_and_finial_are_parameters() -> None:
    plain = StylizedBishop(dimensions=BishopDimensions(slit=False))
    assert _volume(plain) > _volume(StylizedBishop())
    tall = StylizedBishop(dimensions=BishopDimensions(finial_half_height=7.0))
    shape = tall.shape()
    assert shape is not None
    bounds = shape.bounds()
    assert bounds is not None
    assert bounds[5] == pytest.approx(82.5 + 1.5, abs=1e-3)


def test_other_body_and_head_dimensions_build() -> None:
    body = ChessBodyDimensions(
        base_radius=18,
        platform_radius=13.5,
        stem_bottom_radius=10,
        back_row_shoulder_z=48,
        stem_curve=0.2,
    )
    pieces = [
        StylizedPawn(body, PawnDimensions(ball_radius=11)),
        StylizedRook(body, RookDimensions(head_width=24, crenel_width=6)),
        StylizedKnight(body, KnightDimensions(head_thickness=11, bevel=1.2)),
        StylizedBishop(body),
        StylizedQueen(body, QueenDimensions(notch_count=6, notch_phase=0)),
        StylizedKing(body, KingDimensions(bar_height=26, arm_offset=12)),
    ]
    for piece in pieces:
        shape = piece.shape()
        assert shape is not None
        bounds = shape.bounds()
        assert bounds is not None
        assert bounds[3] == pytest.approx(18, abs=1e-4)
        _solid(piece)


def test_pawn_ball_flat_matches_stem_top() -> None:
    d = PawnDimensions()
    flat = 2 * math.sqrt(d.ball_radius**2 - d.ball_center_above_shoulder() ** 2)
    assert flat == pytest.approx(2 * d.stem_top_radius)


def test_stem_profile_spans_platform_to_shoulder() -> None:
    body = ChessBodyDimensions()
    profile = body.stem_profile(6.0, 43.0)
    assert len(profile) == body.stem_samples + 1
    assert profile[0] == (9.0, body.platform_top - body.stem_overlap)
    assert profile[-1] == (6.0, 43.0 + body.stem_overlap)
    # Concave: the stem narrows faster near the platform than near the shoulder.
    assert profile[1][0] - profile[2][0] > profile[-2][0] - profile[-1][0]


def test_bezier_helpers() -> None:
    assert quadratic_bezier((0, 0), (1, 1), (2, 0), 4)[2] == (1.0, 0.5)
    curve = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
    points = cubic_bezier(curve, 2)
    assert points[0] == (0.0, 0.0) and points[-1] == (1.0, 0.0)
    assert points[1] == pytest.approx((0.5, 0.75))
    with pytest.raises(ValueError):
        cubic_bezier(curve, 0)
    with pytest.raises(ValueError):
        quadratic_bezier((0, 0), (1, 1), (2, 0), 0)


def test_bishop_head_starts_at_stem_top() -> None:
    d = BishopDimensions(stem_top_radius=4.0)
    profile = d.head_profile()
    assert profile[0] == (4.0, 0.0)
    assert profile[-1] == (0.0, 31.0)


@pytest.mark.parametrize(
    "make",
    [
        lambda: ChessBodyDimensions(platform_radius=15),
        lambda: ChessBodyDimensions(edge_round=2.5),
        lambda: ChessBodyDimensions(pin_socket_depth=12),
        lambda: ChessBodyDimensions(pin_socket_depth=-1),
        lambda: ChessBodyDimensions(stem_curve=1.5),
        lambda: ChessBodyDimensions(base_height=-6),
        lambda: ChessBodyDimensions(pawn_shoulder_z=10),
        lambda: ChessBodyDimensions(base_top_chamfer=float("nan")),
        lambda: PawnDimensions(ball_radius=4),
        lambda: RookDimensions(crenel_width=30),
        lambda: RookDimensions(crenel_depth=20),
        lambda: KnightDimensions(bevel=5),
        lambda: KnightDimensions(bevel=1.5),  # mane notch edges are ~2.5 mm
        lambda: KnightDimensions(eye_depth=5),
        lambda: KnightDimensions(head_outline=((0.0, 0.0), (1.0, 1.0))),
        lambda: BishopDimensions(slit_angle=95),
        lambda: BishopDimensions(head_upper=((9.0, 25.0), (4.0, 30.0), (1.0, 31.0))),
        lambda: QueenDimensions(crown_offset=8),
        lambda: QueenDimensions(notch_depth=25),
        lambda: QueenDimensions(notch_length=5),
        lambda: KingDimensions(arm_offset=20),
        lambda: KingDimensions(arm_span=5),
        lambda: KingDimensions(bevel=3.5),
        lambda: KingDimensions(cross_embed=2),
    ],
)
def test_bad_dimensions_are_rejected(make: object) -> None:
    with pytest.raises(ValueError):
        make()  # type: ignore[operator]


def test_pieces_check_dimensions_against_the_body() -> None:
    small = ChessBodyDimensions(base_radius=12, platform_radius=9, stem_bottom_radius=6)
    with pytest.raises(ValueError, match="knight head"):
        StylizedKnight(small, KnightDimensions(stem_top_radius=5, shoulder_radius=9))
    with pytest.raises(ValueError, match="shoulder"):
        StylizedKing(dimensions=KingDimensions(shoulder_radius=7))
    with pytest.raises(ValueError, match="stem top"):
        StylizedRook(small)
    with pytest.raises(ValueError, match="overhang"):
        StylizedRook(dimensions=RookDimensions(head_width=14))
    with pytest.raises(ValueError, match="wider than the base"):
        StylizedQueen(dimensions=QueenDimensions(shoulder_radius=17))


def test_knight_outline_reaches_the_snout() -> None:
    assert max(x for x, _ in KNIGHT_OUTLINE) == 16.0
    assert max(z for _, z in KNIGHT_OUTLINE) == 31.0


def test_set_has_sixteen_pieces_and_exports(tmp_path: Path) -> None:
    entries = stacking_chess_set()
    assert sum(e.quantity for e in entries) == 16
    paths = export_stacking_chess_stls(str(tmp_path / "stl"))
    assert [Path(p).name for p in paths] == [f"piece_{e.name}.stl" for e in entries]
    assert all(Path(p).stat().st_size > 10_000 for p in paths)
