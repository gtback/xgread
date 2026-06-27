# Contributing to xgread

Thanks for your interest in improving `xgread`. This is a small, focused library;
the guidelines below keep it that way.

## Development setup

```sh
pip install -e ".[dev]"
```

Pure Python, no runtime dependencies. `pytest` and `mypy` are the only dev tools.

## Running the checks

```sh
pytest tests/      # tests
mypy xgread/       # type checks
```

The `.xg` / `.xgp` tests skip automatically when no sample fixture is present (the
sample files contain personal match data and are not committed). To run them against
your own files, point at them with the `XG_SAMPLE` / `XGP_SAMPLE` environment
variables.

## The offset rule

Every binary offset in `xgread/_parser.py` is derived from the official XG format
sources checked into the repo — `xg_format.pas` (record offsets and Pascal alignment)
and `ZLIBArchive.pas` (the archive container). **Only change parser offsets against
the `.pas` source, never by guessing.** Getting an offset wrong silently corrupts
every field after it.

## Scope rule

`xgread` produces a *faithful representation* of the XG format. It may add
derivations that are **pure functions of the format's structure** (canonical,
objective). It must **not** include presentation/rendering or analysis /
value-judgment logic — those belong in downstream consumers. When in doubt, keep the
parser unopinionated and push interpretation to an example script or consumer.

## Changes that affect users

- Update [`CHANGELOG.md`](CHANGELOG.md) under `## [Unreleased]`.
- Follow [Semantic Versioning](https://semver.org/): breaking API changes bump the
  major version (pre-1.0, the minor version), new features the minor, fixes the patch.

## More context

[`AGENTS.md`](AGENTS.md) has the deeper architecture and format notes — package
layout, parser gotchas (Pascal alignment, endianness, the `NOT_ANALYSED` sentinel,
the Unicode-vs-ANSI name fallback), and conventions.
