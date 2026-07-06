#!/usr/bin/env python3
"""Analyze an eXtremeGammon .xg or .xgp file.

Prints every position with the played move, flags blunders and user-flagged
moves, and shows the top engine candidates with their equities.

Usage:
    python analyze_xg.py FILE [--threshold FLOAT] [--top INT]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import xgread
from xgread import CubeAction, Move
from xgread._parser import NOT_ANALYSED

# ── Board rendering ───────────────────────────────────────────────────────────

_MAX_HEIGHT = 5  # rows of checkers shown per point


def _checker_char(value: int, player: int) -> str:
    """X=Player1 always, O=Player2 always, regardless of who is on roll."""
    is_p1 = (value > 0 and player == 1) or (value < 0 and player == -1)
    return "X" if is_p1 else "O"


def _point_col(pos_points: tuple[int, ...], pt: int, row: int, from_top: bool, player: int) -> str:
    """Return the display char for point pt at display row (0 = outermost)."""
    v = pos_points[pt]
    count = min(abs(v), _MAX_HEIGHT)
    if from_top:
        show = row < count
    else:
        show = (_MAX_HEIGHT - 1 - row) < count
    return _checker_char(v, player) if show else "."


def format_board(pos: xgread.Position, player: int,
                 p1_name: str, p2_name: str,
                 cube_level: int, cube_owner: int) -> str:
    """Render board from on-roll player's perspective.

    X=Player1, O=Player2 consistently.  Player names appear on their side.
    Cube value appears beside the row for the owning player (middle if centred).
    cube_owner: 0=centred, 1=player1 owns, -1=player2 owns.
    """
    p = pos.points
    top = list(range(13, 25))
    bot = list(range(12, 0, -1))

    def row_str(pts: list[int], from_top: bool, row: int) -> str:
        left = "  ".join(_point_col(p, pt, row, from_top, player) for pt in pts[:6])
        right = "  ".join(_point_col(p, pt, row, from_top, player) for pt in pts[6:])
        return f"| {left}  |  {right} |"

    # Player labels and cube character
    on_roll_char = "X" if player == 1 else "O"
    opp_char     = "O" if player == 1 else "X"
    on_roll_name = p1_name if player == 1 else p2_name
    opp_name     = p2_name if player == 1 else p1_name

    cube_str = f"[{cube_level}]"
    # rows list indices: 0=header, 1-5=top half, 6=bar, 7-11=bottom half, 12=footer
    # Place cube at middle-of-top (3), bar (6), or middle-of-bottom (9).
    if cube_owner == 0:
        cube_row = 6
    elif cube_owner == player:
        cube_row = 9   # on-roll player owns → bottom half
    else:
        cube_row = 3   # opponent owns → top half

    header = "+13-14-15-16-17-18--+--19-20-21-22-23-24+"
    footer = "+12-11-10--9--8--7--+---6--5--4--3--2--1+"
    rows = [header]
    for r in range(_MAX_HEIGHT):
        rows.append(row_str(top, from_top=True, row=r))
    rows.append("|" + " " * 19 + "|" + " " * 19 + "|")
    for r in range(_MAX_HEIGHT):
        rows.append(row_str(bot, from_top=False, row=r))
    rows.append(footer)

    rows[cube_row] += f"  {cube_str}"

    bar_line = f"  Bar: {on_roll_char}={p[25]}  {opp_char}={abs(p[0])}"
    top_label = f"{opp_char}: {opp_name}"
    bot_label = f"{on_roll_char}: {on_roll_name}"

    return "\n".join([top_label, *rows, bot_label, bar_line])


# ── Move notation ─────────────────────────────────────────────────────────────

def _pt_name(pt: int) -> str:
    if pt < 0:
        return "off"
    if pt == 24:  # player bar in 0-based coordinates
        return "bar"
    return str(pt + 1)


def format_move_notation(moves: tuple[xgread.MoveDetail, ...], pos_before: xgread.Position | None = None) -> str:
    if not moves:
        return "(no moves)"

    if pos_before is None:
        return " ".join(f"{_pt_name(md.from_point)}/{_pt_name(md.die)}" for md in moves)

    # Working copy of board (PositionEngine: index 0=opp bar, 1-24=points, 25=player bar)
    board = list(pos_before.points)

    def board_at(pt_0: int) -> int:
        """Board value at 0-based point index."""
        if pt_0 < 0 or pt_0 >= 24:
            return 0
        return board[pt_0 + 1]

    def apply_move(from_0: int, to_0: int) -> bool:
        """Move one checker; return True if opponent blot was hit."""
        src = from_0 + 1  # player bar (from_0=24) → board[25]; regular → board[from_0+1]
        if 1 <= src <= 25:
            board[src] -= 1
        if to_0 < 0:
            return False  # bearing off — no destination slot to update
        dst = to_0 + 1
        if not (1 <= dst <= 24):
            return False
        hit = board[dst] == -1
        if hit:
            board[dst] = 1
            board[0] -= 1  # send opponent checker to their bar
        else:
            board[dst] += 1
        return hit

    move_list = sorted(((md.from_point, md.die) for md in moves), key=lambda x: -x[0])
    n = len(move_list)
    parts = []
    i = 0

    while i < n:
        chain_from = move_list[i][0]
        cur_to = move_list[i][1]

        # Extend chain: follow the same checker through any number of hops.
        # Moves may be stored out-of-order (XG records physical play order); scan
        # ahead for the continuation and swap it into the next slot.
        # Stop only when hitting an opponent blot at the intermediate point.
        while cur_to >= 0 and board_at(cur_to) != -1:
            j = next((k for k in range(i + 1, n) if move_list[k][0] == cur_to), None)
            if j is None:
                break
            move_list[i + 1], move_list[j] = move_list[j], move_list[i + 1]
            apply_move(move_list[i][0], cur_to)
            i += 1
            cur_to = move_list[i][1]

        # Apply the final (or only) segment; detect hit at destination
        hit = cur_to >= 0 and board_at(cur_to) == -1
        apply_move(move_list[i][0], cur_to)

        parts.append((chain_from, f"{_pt_name(chain_from)}/{_pt_name(cur_to)}{'*' if hit else ''}"))
        i += 1

    # Sort segments by from-point descending for canonical ordering.
    # This makes equivalent moves (same checkers, different storage order) compare equal.
    parts.sort(key=lambda x: (-x[0], x[1]))
    return " ".join(seg for _, seg in parts)


# ── Error / flag marker ───────────────────────────────────────────────────────

def format_marker(error: float, flagged: bool, threshold: float) -> str:
    parts = []
    if flagged:
        parts.append("FLAGGED")
    if error != NOT_ANALYSED and abs(error) >= threshold:
        parts.append(f"BLUNDER ({error:+.3f})")
    return "  *** " + "  ".join(parts) + " ***" if parts else ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze an eXtremeGammon .xg or .xgp file."
    )
    parser.add_argument("file", help="Path to .xg or .xgp file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        metavar="FLOAT",
        help="Equity error threshold to flag as blunder (default: 0.05)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="INT",
        help="Number of top engine candidates to show (default: 5)",
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    match = xgread.read(path)
    hdr = match.header
    ml = hdr.match_length if hdr.match_length < 99999 else "∞"
    print(f"{hdr.player1} vs {hdr.player2}  |  Match to {ml}  |  {hdr.event or 'No event'}")
    print(f"Games: {len(match.games)}  |  Match ID: {match.identity_hash}")

    # The canonical XGID for each decision, keyed so we can show it inline below.
    xgid_by_event = {id(d.event): d.xgid for d in match.decisions()}

    for game in match.games:
        gh = game.header
        score = f"{gh.score1}-{gh.score2}"
        print(f"\n{'='*60}")
        print(f"Game {gh.game_number}  (score: {score})")
        print(f"{'='*60}")

        move_num = 0
        for event in game.events:
            if isinstance(event, Move):
                move_num += 1
                player_name = hdr.player1 if event.player == 1 else hdr.player2
                pos = event.position_before
                played = format_move_notation(event.moves, pos)

                cv = event.cube_value
                cube_level = (2 ** abs(cv)) if cv != 0 else 1
                cube_owner = (event.player if cv > 0 else -event.player) if cv != 0 else 0

                # Find which candidate was played by comparing normalized notation
                # (handles equivalent paths like 13/9 9/7 == 13/11 11/7 == 13/7)
                played_idx = None
                for ci, cand in enumerate(event.candidates):
                    if format_move_notation(cand.moves, pos) == played:
                        played_idx = ci
                        break

                best_was_played = played_idx == 0

                if best_was_played and not event.flagged:
                    # Compact: just roll and move
                    print(f"  {player_name} {event.dice[0]}-{event.dice[1]}: {played}")
                else:
                    luck_str = (
                        f"  luck: {event.luck:+.3f}" if event.luck != NOT_ANALYSED else ""
                    )
                    error_str = (
                        f"  error: {event.error:+.3f}" if event.error != NOT_ANALYSED else "  (not analysed)"
                    )
                    marker = format_marker(event.error, event.flagged, args.threshold)
                    print(f"\n--- Move {move_num}  {player_name}  {event.dice[0]}-{event.dice[1]} ---")
                    print(xgid_by_event[id(event)])
                    print(format_board(pos, event.player,
                                      hdr.player1, hdr.player2,
                                      cube_level, cube_owner))
                    print(f"Played: {played}{error_str}{luck_str}{marker}")

                    if event.candidates:
                        n_show = min(args.top, len(event.candidates))
                        played_in_top = played_idx is not None and played_idx < n_show
                        best_eq = event.candidates[0].evaluation.equity
                        print(f"  Top {n_show} moves:")
                        for rank, cand in enumerate(event.candidates[:n_show], 1):
                            notation = format_move_notation(cand.moves, pos)
                            played_mark = " <-- played" if (rank - 1) == played_idx else ""
                            if rank == 1:
                                eq_str = f"equity: {cand.evaluation.equity:+.3f}"
                            else:
                                eq_str = f"equity: {cand.evaluation.equity:+.3f}  ({-cand.equity_loss:+.3f})"
                            print(f"    {rank}. {notation:<22} {eq_str}{played_mark}")
                        if not played_in_top:
                            if played_idx is not None:
                                cand = event.candidates[played_idx]
                                notation = format_move_notation(cand.moves, pos)
                                print(f"    {played_idx + 1}. {notation:<22} equity: {cand.evaluation.equity:+.3f}  ({-cand.equity_loss:+.3f}) <-- played")
                            elif event.error != NOT_ANALYSED:
                                best_eq_str = f"{best_eq:+.3f}" if event.candidates else "n/a"
                                played_eq = best_eq + event.error if event.candidates else None
                                eq_part = f"equity: {played_eq:+.3f}  ({event.error:+.3f})" if played_eq is not None else f"({event.error:+.3f})"
                                print(f"    (played) {played:<22} {eq_part} <-- played")

            elif isinstance(event, CubeAction):
                analysed = event.error_double != NOT_ANALYSED
                show = (
                    event.doubled
                    or event.flagged
                    or (analysed and abs(event.error_double) >= args.threshold)
                )
                if not show:
                    continue

                player_name = hdr.player1 if event.player == 1 else hdr.player2
                opp_name = hdr.player2 if event.player == 1 else hdr.player1
                cv = event.cube_value
                cube_level = (2 ** abs(cv)) if cv != 0 else 1

                if event.doubled:
                    took_str = " — took" if event.took else " — dropped"
                    print(f"\n--- Cube  {player_name}  doubled{took_str} (cube: {cube_level * 2}) ---")
                else:
                    marker = format_marker(event.error_double, event.flagged, args.threshold)
                    print(f"\n--- Cube  {player_name}  no double{marker} ---")
                print(xgid_by_event[id(event)])

                if analysed:
                    d_cands = sorted([
                        ("Double/Take", event.double_take_equity),
                        ("Double/Drop", event.double_drop_equity),
                        ("No double",   event.no_double_equity),
                    ], key=lambda x: -x[1])
                    played_d = (
                        ("Double/Take" if event.took else "Double/Drop")
                        if event.doubled else "No double"
                    )
                    played_d_idx = next(i for i, (n, _) in enumerate(d_cands) if n == played_d)
                    best_d_eq = d_cands[0][1]
                    err_str = f"  error: {event.error_double:+.3f}" if event.error_double != 0.0 else ""
                    d_marker = format_marker(event.error_double, event.flagged, args.threshold)
                    print(f"  Double decision ({player_name}):{err_str}{d_marker}")
                    for rank, (name, eq) in enumerate(d_cands, 1):
                        mark = " <-- played" if rank - 1 == played_d_idx else ""
                        eq_str = (
                            f"equity: {eq:+.3f}"
                            if rank == 1
                            else f"equity: {eq:+.3f}  ({eq - best_d_eq:+.3f})"
                        )
                        print(f"    {rank}. {name:<18} {eq_str}{mark}")

                if event.doubled and event.took is not None and event.error_take != NOT_ANALYSED:
                    t_cands = sorted([
                        ("Take", -event.double_take_equity),
                        ("Drop", -event.double_drop_equity),
                    ], key=lambda x: -x[1])
                    played_t = "Take" if event.took else "Drop"
                    played_t_idx = next(i for i, (n, _) in enumerate(t_cands) if n == played_t)
                    best_t_eq = t_cands[0][1]
                    err_str = f"  error: {event.error_take:+.3f}" if event.error_take != 0.0 else ""
                    t_marker = format_marker(event.error_take, False, args.threshold)
                    took_verb = "took" if event.took else "dropped"
                    print(f"  Take decision ({opp_name}): {took_verb}{err_str}{t_marker}")
                    for rank, (name, eq) in enumerate(t_cands, 1):
                        mark = " <-- played" if rank - 1 == played_t_idx else ""
                        eq_str = (
                            f"equity: {eq:+.3f}"
                            if rank == 1
                            else f"equity: {eq:+.3f}  ({eq - best_t_eq:+.3f})"
                        )
                        print(f"    {rank}. {name:<18} {eq_str}{mark}")

        if game.footer:
            gf = game.footer
            winner = hdr.player1 if gf.winner == 1 else hdr.player2
            print(f"\nResult: {winner} wins {gf.points_won} point(s)")


if __name__ == "__main__":
    main()
