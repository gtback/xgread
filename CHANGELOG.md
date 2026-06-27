# Changelog

All notable changes to `xgread` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Public-contract note:** when the match-identity hash and XGID encoding land,
> their canonical forms (field order, normalization, the play-vs-analysis boundary)
> become part of the public API. Changing a frozen canonical form re-keys every
> consumer, so such changes will be treated as breaking and versioned accordingly.

## [Unreleased]

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

[Unreleased]: https://github.com/gtback/xgread/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gtback/xgread/releases/tag/v0.1.0
