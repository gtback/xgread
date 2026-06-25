from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Position:
    """Board state from the on-roll player's POV.

    Index 0 = opponent bar, 1–24 = points (1=ace point), 25 = player's bar.
    Negative values = opponent checkers; positive = player's checkers; 0 = empty.
    """
    points: tuple[int, ...]  # length 26


@dataclass(frozen=True)
class MoveDetail:
    """A single checker move: source and destination points (both 0-based, 0=ace)."""
    from_point: int
    die: int  # destination point (0-based); named 'die' to match XG's raw field


@dataclass(frozen=True)
class Evaluation:
    """7-element probability/equity vector from the XG engine.

    Indices: 0=lose_bg, 1=lose_gammon, 2=lose_single,
             3=win_single, 4=win_gammon, 5=win_bg, 6=equity
    """
    lose_bg: float
    lose_gammon: float
    lose_single: float
    win_single: float
    win_gammon: float
    win_bg: float
    equity: float

    @classmethod
    def from_seq(cls, seq: tuple[float, ...]) -> "Evaluation":
        return cls(*seq[:7])


@dataclass(frozen=True)
class MoveCandidate:
    """One engine-ranked candidate move and its evaluation (best-first order)."""
    moves: tuple[MoveDetail, ...]
    evaluation: Evaluation


@dataclass(frozen=True)
class Move:
    """A checker-play decision."""
    player: int                       # 1=player1, -1=player2
    position_before: Position
    position_after: Position
    dice: tuple[int, int]
    moves: tuple[MoveDetail, ...]
    cube_value: int                   # cube state: 0=centre, +n=player owns 2^n, -n=opp owns 2^n
    error: float                      # equity error; -1000.0 = not analysed
    luck: float                       # luck of the roll; -1000.0 = not analysed
    analysis: Evaluation | None       # engine evaluation of played move
    candidates: tuple[MoveCandidate, ...]  # all engine candidates, best-first; empty if not analysed
    flagged: bool
    comment_index: int                # index into .xgc file; -1 = none


@dataclass(frozen=True)
class CubeAction:
    """A cube-related decision (double/take/beaver)."""
    player: int                       # active player: 1 or -1
    doubled: bool
    took: bool | None                 # None if no double offered
    beavered: bool
    cube_value: int                   # 0=centre, +n=player owns 2^n, -n=opp owns 2^n
    position: Position
    error_double: float               # equity error on doubling; -1000.0 = not analysed
    error_take: float                 # equity error on taking; -1000.0 = not analysed
    no_double_equity: float
    double_take_equity: float
    double_drop_equity: float
    flagged: bool
    comment_index: int


@dataclass(frozen=True)
class GameHeader:
    score1: int
    score2: int
    crawford_apply: bool
    initial_position: Position
    game_number: int                  # 1-based
    in_progress: bool
    n_auto_doubles: int
    comment_index: int


@dataclass(frozen=True)
class GameFooter:
    score1: int
    score2: int
    winner: int                       # +1=player1, -1=player2
    points_won: int
    termination: int                  # 0=Drop,1=Single,2=Gammon,3=BG; +100=Resign,+1000=Settle
    comment_index: int


@dataclass(frozen=True)
class Game:
    header: GameHeader
    events: tuple[Move | CubeAction, ...]
    footer: GameFooter | None  # None for in-progress games


@dataclass(frozen=True)
class MatchHeader:
    player1: str
    player2: str
    match_length: int                 # 99999 = unlimited money session
    variation: int                    # 0=backgammon,1=nack,2=hyper,3=longgammon
    crawford: bool
    jacoby: bool
    beaver: bool
    elo1: float
    elo2: float
    experience1: int
    experience2: int
    date: datetime | None
    event: str
    location: str
    round_name: str
    game_mode: int                    # 0=Free … 6=Custom
    version: int                      # SaveFileVersion
    magic: int                        # must equal 0x494C4D44
    site_id: int
    cube_limit: int
    comment_header_index: int
    comment_footer_index: int


@dataclass(frozen=True)
class MatchFooter:
    score1: int
    score2: int
    winner: int
    elo1: float
    elo2: float
    experience1: int
    experience2: int
    date: datetime | None


@dataclass(frozen=True)
class Match:
    header: MatchHeader
    games: tuple[Game, ...]
    footer: MatchFooter | None
    thumbnail: bytes                  # raw JPG bytes; empty if not present


# ── Lookup tables ────────────────────────────────────────────────────────────

PLAYER_LEVELS: dict[int, str] = {
    0: "1-ply", 1: "2-ply", 2: "3-ply", 12: "3-ply red",
    3: "4-ply", 4: "5-ply", 5: "6-ply", 6: "7-ply",
    100: "Rollout", 998: "Opening Book V2", 999: "Opening Book V1",
    1000: "XGRoller", 1001: "XGRoller+", 1002: "XGRoller++",
}

GAME_MODES: dict[int, str] = {
    0: "Free", 1: "Tutor", 2: "Teaching", 3: "Coaching",
    4: "Competition", 5: "IronMan", 6: "Custom",
}

VARIATIONS: dict[int, str] = {
    0: "Backgammon", 1: "Nackgammon", 2: "Hypergammon", 3: "Longgammon",
}

SITE_NAMES: dict[int, str] = {
    0: "GammonSite", 1: "FIBS", 2: "TrueMoney Games", 3: "GridGammon",
    4: "DailyGammon", 5: "NetGammon", 6: "VOG", 7: "Gammon Empire/Play65",
    8: "Club Games", 9: "PartyGammon", 10: "XcitingGames", 11: "BGRoom",
    12: "DiceArena", 13: "Safe Harbor Games", 14: "GameAccount", 15: "XG Mobile",
}

TERMINATION_NAMES: dict[int, str] = {
    0: "Drop", 1: "Single", 2: "Gammon", 3: "Backgammon",
    100: "Resign Single", 101: "Resign Single", 102: "Resign Gammon",
    103: "Resign Backgammon", 1000: "Settle",
}
