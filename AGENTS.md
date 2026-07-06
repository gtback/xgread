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
  - `_notation.py` — standard move notation (`format_moves`, `Move.notation`) and
    played-candidate matching (`Move.played_index`).
- `tests/` — `pytest` smoke tests; `sample.xg` / `sample.xgp` fixtures.
- `examples/` — tracked example scripts that use `xgread` (`analyze_xg.py`).

## Public API cheat-sheet (so you needn't spelunk `models.py`)

Entry: `xgread.read(path)` → `Match` (auto-detects `.xg`/`.xgp` from bytes).

- `Match`: `.header`, `.games`, `.footer`, `.thumbnail`; `.identity_hash` (stable,
  versioned, analysis-independent match id); `.decisions()` → `Decision` per move/cube.
- `Decision`: `.game_number`, `.move_number` (**counts cube actions too**), `.score1/2`,
  `.event` (`Move | CubeAction`), `.xgid`.
- `Game`: `.header`, `.events` (`Move | CubeAction`, ordered), `.footer`; `.moves`,
  `.cube_actions`, `.position_after(n)`.
- `Move`: `.player`, `.position_before/after`, `.dice`, `.moves`, `.cube_value`,
  `.error`/`.luck` (`NOT_ANALYSED` sentinel), `.candidates` (best-first `MoveCandidate`),
  `.flagged`; derived: `.is_analysed`, `.played_index` (`int | None`), `.analysis`
  (played move's `Evaluation`), `.notation`.
- `MoveCandidate`: `.moves`, `.evaluation`, `.equity_loss` (vs `candidates[0]`; `0.0` for it).
- `CubeAction`: `.player`, `.doubled`, `.took` (`bool | None`), `.cube_value`,
  `.error_double`/`.error_take`, `.no_double_equity`/`.double_take_equity`/
  `.double_drop_equity`; derived `.is_analysed`.
- Helpers: `xgread.format_moves(moves, position)` (notation for any move set),
  `xgread.NOT_ANALYSED`.

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

## Field-semantics traps (the record lies about what some fields mean)

- **`CompChoice` is the *computer's* recommended move, not the played move.** The played
  move lives only as raw checker hops (`Move.moves`); `Move.played_index` recovers which
  candidate that is by matching. (A past bug populated `Move.analysis` from `CompChoice`.)
- **`Evaluation` is XG's raw *cumulative* 7-vector** (`lose_bg…win_bg, equity`), not
  discrete win/gammon/bg splits. Don't present these as probabilities without deriving.
- **`MoveDetail.die` is a destination point**, not a die value (named after XG's raw field).
- **`cube_value` is log-encoded**: `0`=centre, `+n`=player owns `2^n`, `-n`=opp owns.

## Conventions

- Relative imports inside the package (`.models`, `._parser`, `._archive`).
- Models are frozen dataclasses.
- Match the surrounding comment density and idiom — `_parser.py` documents its
  offsets inline because they're easy to get wrong.

### Adding a derivation (the `identity_hash` / `notation` / `played_index` pattern)

A new canonical derivation should be **a `@property` on the model** (or a small pure
function in a `_*.py` module), with a **lazy import** inside the property to avoid import
cycles (see `Match.identity_hash`, `Move.notation`). Then:
1. Export any public function from `__init__.py` and add it to `__all__`.
2. Update the README data-model section and add a `CHANGELOG.md` entry.
3. Validate against real data: the `sample.xg` invariant tests (e.g.
   `test_played_index_identifies_played_move`) are the pattern — assert a property against
   an independent signal, not against itself.
4. Run **both** `pytest` and `mypy` (the package ships typed).

## Scope rule

`xgread` parses the XG format into a faithful Python representation. It may add
derivations that are **pure functions of the format's structure** (canonical,
objective). It must **not** include presentation/rendering or analysis /
value-judgment logic — those belong in downstream consumers. Example consumers
will be added or linked to later.

## Known gaps (deferred, not bugs)

- **`Move.played_index` is recovered by matching**, not read from the file. `CompChoice`
  in the record is the *computer's* choice, not the played move; the played move is only
  stored as its raw checker hops. `None` result means the played move wasn't among the
  listed candidates (a transposition; always near-zero error in practice).
- **Cube decisions expose only the three scalar equities** (`no_double_equity`,
  `double_take_equity`, `double_drop_equity`), not the raw `Eval`/`EvalDouble` 7-vectors
  the record also holds. Surface those if a consumer needs cube-position probabilities.
- **`MoveDetail.die` is a destination point**, not a die value (named after XG's raw field).
- **`Decision.move_number` counts cube actions too**, so it is not a pure checker-move
  ordinal.

## Verifying changes

```sh
pytest tests/
mypy xgread/ examples/
```

## For human contributors

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup, the test/type-check
commands, the offset rule, and the changelog/versioning expectations.
