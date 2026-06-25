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
