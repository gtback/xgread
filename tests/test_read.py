"""Smoke tests for xgread.

Run with:  pytest tests/
To point at your own sample files, set the XGP_SAMPLE and XG_SAMPLE
environment variables, or place files at tests/sample.xgp / tests/sample.xg.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import xgread
from xgread import CubeAction, Match, Move
from xgread._parser import MAGIC_NUMBER, RICH_HDR_SIZE, SAVE_REC_SIZE

TESTS_DIR = Path(__file__).parent
XGP_PATH = Path(os.environ.get("XGP_SAMPLE", TESTS_DIR / "sample.xgp"))
XG_PATH  = Path(os.environ.get("XG_SAMPLE",  TESTS_DIR / "sample.xg"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _skip_if_missing(p: Path):
    if not p.exists():
        pytest.skip(f"Sample file not found: {p}")


# ── .xgp tests ────────────────────────────────────────────────────────────────

class TestReadXgp:
    def setup_method(self):
        _skip_if_missing(XGP_PATH)
        self.match = xgread.read(str(XGP_PATH))

    def test_returns_match(self):
        assert isinstance(self.match, Match)

    def test_player_names_non_empty(self):
        assert self.match.header.player1
        assert self.match.header.player2

    def test_has_games(self):
        assert len(self.match.games) > 0

    def test_match_length_positive(self):
        assert self.match.header.match_length > 0

    def test_magic_number(self):
        assert self.match.header.magic == MAGIC_NUMBER

    def test_version_in_range(self):
        assert 1 <= self.match.header.version <= 40

    def test_games_have_events(self):
        for game in self.match.games:
            assert len(game.events) > 0, f"Game {game.header.game_number} has no events"

    def test_game_footer_winner_valid(self):
        for game in self.match.games:
            if game.footer is None:
                continue  # in-progress game
            assert game.footer.winner in (-1, 1)

    def test_events_are_typed(self):
        for game in self.match.games:
            for event in game.events:
                assert isinstance(event, (Move, CubeAction))

    def test_move_dice_valid(self):
        for game in self.match.games:
            for event in game.events:
                if isinstance(event, Move):
                    d1, d2 = event.dice
                    assert 1 <= d1 <= 6
                    assert 1 <= d2 <= 6

    def test_position_length(self):
        for game in self.match.games:
            for event in game.events:
                if isinstance(event, Move):
                    assert len(event.position_before.points) == 26
                    assert len(event.position_after.points) == 26

    def test_thumbnail_bytes(self):
        # Thumbnail may be empty but should be bytes
        assert isinstance(self.match.thumbnail, bytes)


# ── .xg tests ─────────────────────────────────────────────────────────────────

class TestReadXg:
    def setup_method(self):
        _skip_if_missing(XG_PATH)
        self.match = xgread.read(str(XG_PATH))

    def test_returns_match(self):
        assert isinstance(self.match, Match)

    def test_player_names_non_empty(self):
        assert self.match.header.player1
        assert self.match.header.player2

    def test_has_games(self):
        assert len(self.match.games) > 0

    def test_xg_inner_stream_multiple_of_record_size(self):
        from xgread._archive import open_archive
        from xgread._parser import parse_rich_header
        data = XG_PATH.read_bytes()
        _, thumb_size = parse_rich_header(data)
        files = open_archive(data[RICH_HDR_SIZE + thumb_size:])
        assert len(files["temp.xg"]) % SAVE_REC_SIZE == 0

    def test_decisions_yield_well_formed_xgids(self):
        from xgread import Move
        n = 0
        for d in self.match.decisions():
            n += 1
            assert d.xgid.startswith("XGID=")
            body = d.xgid[len("XGID="):]
            position, *fields = body.split(":")
            assert len(position) == 26
            assert len(fields) == 9            # cube..maxcube
            assert fields[2] == "1"            # turn: always the mover's perspective
            dice = fields[3]
            if isinstance(d.event, Move):
                assert dice != "00" and len(dice) == 2
            else:
                assert dice == "00"
        assert n > 0

    def test_identity_hash_stable_across_reparse(self):
        again = xgread.read(str(XG_PATH))
        assert self.match.identity_hash == again.identity_hash

    def test_equity_loss_relative_to_best(self):
        for game in self.match.games:
            for move in game.moves:
                if not move.candidates:
                    continue
                best_eq = move.candidates[0].evaluation.equity
                assert move.candidates[0].equity_loss == pytest.approx(0.0)
                for c in move.candidates:
                    assert c.equity_loss == pytest.approx(best_eq - c.evaluation.equity)

    def test_position_after_matches_move(self):
        for game in self.match.games:
            moves = game.moves
            for i, move in enumerate(moves, start=1):
                assert game.position_after(i) == move.position_after
            if moves:
                with pytest.raises(IndexError):
                    game.position_after(len(moves) + 1)

    def test_played_index_identifies_played_move(self):
        seen = 0
        for game in self.match.games:
            for move in game.moves:
                if not move.is_analysed:
                    continue
                pidx = move.played_index
                if pidx is None:
                    continue  # rare: played move is a transposition XG did not list
                seen += 1
                # played_index points at the candidate whose moves are the ones played
                cand = move.candidates[pidx]
                assert xgread.format_moves(cand.moves, move.position_before) == move.notation
                # analysis is that candidate's evaluation
                assert move.analysis is cand.evaluation
                # playing the top candidate <=> zero equity error
                if pidx == 0:
                    assert move.error == pytest.approx(0.0)
        assert seen > 0

    def test_analysis_none_when_unanalysed(self):
        for game in self.match.games:
            for move in game.moves:
                if not move.is_analysed:
                    assert move.analysis is None
                    assert move.played_index is None


# ── Unit tests (no sample files needed) ──────────────────────────────────────

class TestHelpers:
    def test_parse_move_list_basic(self):
        from xgread._parser import _parse_move_list
        raw = (3, 2, 5, 4, -1, 0, 0, 0)
        moves = _parse_move_list(raw)
        assert len(moves) == 2
        assert moves[0].from_point == 3 and moves[0].die == 2
        assert moves[1].from_point == 5 and moves[1].die == 4

    def test_parse_move_list_empty(self):
        from xgread._parser import _parse_move_list
        raw = (-1, 0, 0, 0, 0, 0, 0, 0)
        assert _parse_move_list(raw) == []

    def test_tdatetime_zero(self):
        from xgread._parser import _tdatetime
        assert _tdatetime(0.0) is None

    def test_tdatetime_known(self):
        from datetime import datetime
        from xgread._parser import _tdatetime
        # 35065 days after 1899-12-30 = 1996-01-01
        dt = _tdatetime(35065.0)
        assert dt is not None
        assert dt.year == 1996 and dt.month == 1 and dt.day == 1

    def test_shortstring_decode(self):
        from xgread._parser import _shortstring
        buf = bytearray(50)
        name = b"Alice"
        buf[5] = len(name)
        buf[6 : 6 + len(name)] = name
        assert _shortstring(bytes(buf), 5) == "Alice"

    def test_align4(self):
        from xgread._parser import _align4
        assert _align4(0)  == 0
        assert _align4(1)  == 4
        assert _align4(4)  == 4
        assert _align4(5)  == 8

    def test_align8(self):
        from xgread._parser import _align8
        assert _align8(0)  == 0
        assert _align8(1)  == 8
        assert _align8(8)  == 8
        assert _align8(9)  == 16

    def test_evaluation_from_seq(self):
        vals = (0.1, 0.2, 0.3, 0.4, 0.05, 0.01, 0.55)
        ev = xgread.Evaluation.from_seq(vals)
        assert ev.lose_bg == pytest.approx(0.1)
        assert ev.equity == pytest.approx(0.55)


# ── XGID encoding (no sample files needed) ───────────────────────────────────

# Standard backgammon starting position from the on-roll player's POV.
_START_POINTS = (0, -2, 0, 0, 0, 0, 5, 0, 3, 0, 0, 0, -5,
                 5, 0, 0, 0, -3, 0, -5, 0, 0, 0, 0, 2, 0)
_START_XGID_POS = "-b----E-C---eE---c-e----B-"


class TestXgid:
    def test_encode_standard_start(self):
        from xgread._xgid import encode_position
        assert encode_position(_START_POINTS) == _START_XGID_POS

    def test_encode_requires_26_slots(self):
        from xgread._xgid import encode_position
        with pytest.raises(ValueError):
            encode_position((0, 0, 0))

    def test_encode_player_and_opponent_chars(self):
        from xgread._xgid import encode_position
        pts = [0] * 26
        pts[3] = 4      # 4 on-roll checkers -> 'D'
        pts[20] = -1    # 1 opponent checker -> 'a'
        s = encode_position(tuple(pts))
        assert s[3] == "D"
        assert s[20] == "a"

    def test_build_xgid_standard_start_money_cube_decision(self):
        from xgread._xgid import build_xgid
        xgid = build_xgid(
            points=_START_POINTS,
            cube_value=0,
            dice=None,
            player_score=0,
            opp_score=0,
            match_length=0,
            crawford_game=False,
            jacoby=False,
            beaver=False,
            cube_limit=10,
        )
        assert xgid == f"XGID={_START_XGID_POS}:0:0:1:00:0:0:0:0:10"

    def test_build_xgid_dice_high_die_first(self):
        from xgread._xgid import build_xgid
        xgid = build_xgid(
            points=_START_POINTS,
            cube_value=0,
            dice=(1, 3),
            player_score=2,
            opp_score=4,
            match_length=7,
            crawford_game=False,
            jacoby=False,
            beaver=False,
            cube_limit=10,
        )
        # dice rendered high-first; fields after position: cube/pos/turn/dice/scores/...
        assert xgid == f"XGID={_START_XGID_POS}:0:0:1:31:2:4:0:7:10"

    def test_build_xgid_cube_owner_sign(self):
        from xgread._xgid import build_xgid
        owned = build_xgid(
            points=_START_POINTS, cube_value=1, dice=None,
            player_score=0, opp_score=0, match_length=7,
            crawford_game=False, jacoby=False, beaver=False, cube_limit=10,
        )
        opp = build_xgid(
            points=_START_POINTS, cube_value=-1, dice=None,
            player_score=0, opp_score=0, match_length=7,
            crawford_game=False, jacoby=False, beaver=False, cube_limit=10,
        )
        assert owned.split(":")[1:3] == ["1", "1"]   # cube=2^1, owner=+1
        assert opp.split(":")[1:3] == ["1", "-1"]    # cube=2^1, owner=-1

    def test_build_xgid_money_rules_flag(self):
        from xgread._xgid import build_xgid
        xgid = build_xgid(
            points=_START_POINTS, cube_value=0, dice=None,
            player_score=0, opp_score=0, match_length=0,
            crawford_game=False, jacoby=True, beaver=True, cube_limit=10,
        )
        assert xgid.split(":")[7] == "3"  # jacoby(1) + beaver(2)


class TestEquityLoss:
    def test_best_candidate_is_zero(self):
        from xgread.models import Evaluation, MoveCandidate
        c = MoveCandidate(moves=(), evaluation=Evaluation.from_seq((0,) * 7))
        assert c.equity_loss == 0.0


# ── Match identity hash (no sample files needed) ─────────────────────────────

def _tiny_match(score1: int, score2: int, *, error: float = 0.0):
    """Build a minimal one-game Match with a single checker move."""
    from xgread.models import (
        Game, GameHeader, Match, MatchHeader, Move, Position,
    )
    pos = Position(_START_POINTS)
    move = Move(
        player=1, position_before=pos, position_after=pos, dice=(3, 1),
        moves=(), cube_value=0, error=error, luck=error,
        candidates=(), flagged=False, comment_index=-1,
    )
    header = MatchHeader(
        player1="A", player2="B", match_length=7, variation=0, crawford=True,
        jacoby=False, beaver=False, elo1=0.0, elo2=0.0, experience1=0,
        experience2=0, date=None, event="", location="", round_name="",
        game_mode=0, version=24, magic=0x494C4D44, site_id=0, cube_limit=10,
        comment_header_index=-1, comment_footer_index=-1,
    )
    gh = GameHeader(
        score1=score1, score2=score2, crawford_apply=False,
        initial_position=pos, game_number=1, in_progress=False,
        n_auto_doubles=0, comment_index=-1,
    )
    game = Game(header=gh, events=(move,), footer=None)
    return Match(header=header, games=(game,), footer=None, thumbnail=b"")


class TestIdentityHash:
    def test_versioned_prefix(self):
        h = _tiny_match(0, 0).identity_hash
        assert h.startswith("xgmid1-")

    def test_stable_for_identical_play(self):
        assert _tiny_match(0, 0).identity_hash == _tiny_match(0, 0).identity_hash

    def test_score_changes_hash(self):
        # Same moves, different per-game score => different identity.
        assert _tiny_match(0, 0).identity_hash != _tiny_match(2, 0).identity_hash

    def test_analysis_does_not_change_hash(self):
        # Only analysis fields differ (error/luck) => same identity.
        assert _tiny_match(0, 0).identity_hash == _tiny_match(0, 0, error=-0.5).identity_hash


# ── Move notation (no sample files needed) ───────────────────────────────────

class TestNotation:
    def _pos(self, **points: int):
        """Position with the given board-index (0=opp bar, 1-24=points, 25=player bar)
        slots set; e.g. ``i8=2`` puts two on-roll checkers on the 8-point."""
        from xgread import Position
        pts = [0] * 26
        for key, value in points.items():
            pts[int(key[1:])] = value
        return Position(tuple(pts))

    def test_two_checkers(self):
        from xgread import MoveDetail, Position, format_moves
        pos = Position(_START_POINTS)
        moves = (MoveDetail(from_point=7, die=4), MoveDetail(from_point=5, die=4))
        assert format_moves(moves, pos) == "8/5 6/5"

    def test_hit_is_starred(self):
        from xgread import MoveDetail, format_moves
        pos = self._pos(i8=2, i5=-1)  # opponent blot on the 5-point
        assert format_moves((MoveDetail(7, 4),), pos) == "8/5*"

    def test_bar_and_bear_off(self):
        from xgread import MoveDetail, format_moves
        pos = self._pos(i25=1, i3=1)
        assert format_moves((MoveDetail(24, 20),), pos) == "bar/21"
        assert format_moves((MoveDetail(2, -1),), pos) == "3/off"

    def test_chain_collapses_to_net(self):
        from xgread import MoveDetail, format_moves
        pos = self._pos(i24=2)
        moves = (MoveDetail(23, 17), MoveDetail(17, 12))  # 24/18/13 one checker
        assert format_moves(moves, pos) == "24/13"

    def test_chain_preserves_intermediate_hit(self):
        from xgread import MoveDetail, format_moves
        pos = self._pos(i24=2, i18=-1)  # blot on the 18-point mid-chain
        moves = (MoveDetail(23, 17), MoveDetail(17, 12))
        assert format_moves(moves, pos) == "24/18* 18/13"

    def test_empty_is_dance(self):
        from xgread import Position, format_moves
        assert format_moves((), Position((0,) * 26)) == "(no moves)"
