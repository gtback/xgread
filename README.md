# xgread

Read [eXtremeGammon](https://www.extremegammon.com/) `.xg` and `.xgp` match
files into plain Python objects.

`xgread`'s job is to produce a **faithful representation**: it parses an XG file
into a tree of dataclasses that mirror the format's structure, and exposes pure
derivations over that structure. It holds no opinions about meaning; things like
presentation and "what counts as a blunder" all live in downstream consumers.

## Install

```sh
pip install -e .
```

Pure Python, requires **Python 3.10+**, no runtime dependencies. (`pytest` is an
optional dev dependency.)

## Quick start

```python
import xgread
from xgread import Move, CubeAction

match = xgread.read("game.xg")          # works for .xg and .xgp (format is
                                        # detected from the bytes, not the suffix)

print(match.header.player1, "vs", match.header.player2)

for game in match.games:
    for event in game.events:
        if isinstance(event, Move):
            print(event.dice, event.moves)
        elif isinstance(event, CubeAction):
            print("cube:", event.doubled, event.took)
```

`xgread.read(path)` auto-detects the container. `xgread.read_xg(path)` and
`xgread.read_xgp(path)` are explicit variants.

## Data model

| Object          | What it is                                                            |
| --------------- | --------------------------------------------------------------------- |
| `Match`         | Top level: `header`, `games`, optional `footer`, `thumbnail` bytes.   |
| `MatchHeader`   | Players, match length, variation, rules, ELO, event metadata.         |
| `Game`          | One game: `header`, ordered `events`, optional `footer`.              |
| `Move`          | A checker-play decision: positions, dice, played `moves`, `candidates`.|
| `CubeAction`    | A cube decision (double / take / beaver) with equities.               |
| `MoveCandidate` | One engine-ranked candidate (`moves` + `evaluation`), best-first.     |
| `Evaluation`    | 7-element win/gammon/backgammon + equity vector from the XG engine.   |
| `Position`      | 26-slot board from the on-roll player's point of view.                |

A game's `events` is an ordered tuple of `Move` and `CubeAction` objects;
branch on type while iterating.

## Tests

Sample files live in `tests/`. Run:

```sh
pytest tests/
```

The `.xg`/`.xgp` tests skip automatically if no sample file is present; point at
your own with the `XG_SAMPLE` / `XGP_SAMPLE` environment variables.

## Format references

The binary layout is decoded directly from the official XG format
documentation. `xg_format.pas` (record offsets and Pascal alignment rules) and
`ZLIBArchive.pas` (the ZLB archive container) in this repo come from
<https://www.extremegammon.com/XGformat.aspx>.
