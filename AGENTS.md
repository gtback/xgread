# Notes for agents working on `xgread`

`xgread` parses eXtremeGammon `.xg` / `.xgp` match files into Python dataclasses.
This file collects the context that isn't obvious from reading the code.

## Layout

- `xgread/` — the package.
  - `__init__.py` — public API (`read`, `read_xg`, `read_xgp`, and the model
    re-exports). This is the only intended import surface for consumers.
  - `models.py` — frozen dataclasses (`Match`, `Game`, `Move`, `CubeAction`,
    `Position`, `MoveCandidate`, `Evaluation`, …) plus lookup tables.
  - `_parser.py` — all binary `struct` parsing of the `TSaveRec` stream.
  - `_archive.py` — ZLB archive decompression (the `.xg`/`.xgp` container).
  - `_xgid.py` — canonical XGID encoding (`Match.decisions()` uses it).
  - `_identity.py` — the versioned match-identity hash (`Match.identity_hash`).
- `tests/` — `pytest` smoke tests; `sample.xg` / `sample.xgp` fixtures.
- `examples/` — tracked example scripts that use `xgread` (`analyze_xg.py`).

## Format references

The binary layout is decoded from the official XG format docs at
<https://www.extremegammon.com/XGformat.aspx>. Two source files from there live
in the repo: `xg_format.pas` (struct offsets and Pascal alignment) and
`ZLIBArchive.pas` (the archive container). **Every offset in `_parser.py` is
derived from these — only change parser offsets against the `.pas` source**,
never by guessing.

The XGID string format is *not* in those `.pas` files (it is a separate XG
standard). `_xgid.py` follows `docs/xgid.md` from `gtback/backgammon-js`, which
agrees with GNU Backgammon's `SetXGID` parser (`set.c`). Key point: the board and
the two score fields are written from the **on-roll player's** perspective (not a
fixed player 1), and `xgread` emits every decision from its mover's view, so the
turn field is always `+1`.

## Parser gotchas (already encoded — don't relearn the hard way)

- Pascal default alignment: integers on 4-byte, doubles on 8-byte boundaries;
  `ShortString`/`Boolean`/`byte` do not align. Use `_align4` / `_align8`.
- Everything is little-endian.
- `NOT_ANALYSED = -1000.0` is the sentinel for unanalysed equity/luck fields.
- Player/event names: Unicode fields are used when `version >= 24`, otherwise the
  parser falls back to the older ANSI `ShortString` fields.

## Conventions

- Relative imports inside the package (`.models`, `._parser`, `._archive`).
- Models are frozen dataclasses.
- Match the surrounding comment density and idiom — `_parser.py` documents its
  offsets inline because they're easy to get wrong.

## Scope rule

`xgread` parses the XG format into a faithful Python representation. It may add
derivations that are **pure functions of the format's structure** (canonical,
objective). It must **not** include presentation/rendering or analysis /
value-judgment logic — those belong in downstream consumers. Example consumers
will be added or linked to later.

## Verifying changes

```sh
pytest tests/
```

## For human contributors

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup, the test/type-check
commands, the offset rule, and the changelog/versioning expectations.
