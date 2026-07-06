# Changelog

All notable changes to `xgread` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Public-contract note:** when the match-identity hash and XGID encoding land,
> their canonical forms (field order, normalization, the play-vs-analysis boundary)
> become part of the public API. Changing a frozen canonical form re-keys every
> consumer, so such changes will be treated as breaking and versioned accordingly.

## [Unreleased]

## [0.2.0] - 2026-06-27

### Added
- **XGID per decision.** `Match.decisions()` yields a `Decision` for every move and
  cube action, each carrying its canonical `xgid` string plus the game number,
  per-game match score, and decision index. The XGID encoding (field order,
  on-roll-player perspective, score ordering, dice rendering) is a **frozen public
  contract** — see `xgread/_xgid.py`.
- **Match identity hash.** `Match.identity_hash` is a stable, opaque, versioned
  digest of the *played* match (moves, dice, cube actions, and per-game score
  progression), derived independently of analysis output so it is unchanged by
  re-analysis. The same moves at a different score hash differently. The canonical
  form is a **frozen, versioned public contract** — see `xgread/_identity.py`.
- **Structural traversal accessors.** `Game.moves`, `Game.cube_actions`, and
  `Game.position_after(n)`.
- **`MoveCandidate.equity_loss`** — equity given up versus the engine's best move
  (`candidates[0]`); `0.0` for that move.

The XGID and identity-hash canonical forms are now part of the public API; future
changes to either are breaking and versioned (the identity hash carries its own
version in the string).

## [0.1.0] - 2026-06-26

Initial release.

### Added
- `read()`, `read_xg()`, and `read_xgp()` entry points that parse eXtremeGammon
  `.xg` / `.xgp` files into frozen dataclasses (container format is detected from
  the bytes, not the file suffix).
- Faithful object model: `Match`, `MatchHeader`, `MatchFooter`, `Game`,
  `GameHeader`, `GameFooter`, `Move`, `CubeAction`, `MoveCandidate`, `MoveDetail`,
  `Evaluation`, and `Position`.
- Best-first engine candidates with win/gammon/backgammon odds for both players,
  exposed via `Evaluation`.
- `xgread.__version__`.

[Unreleased]: https://github.com/gtback/xgread/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/gtback/xgread/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/gtback/xgread/releases/tag/v0.1.0
