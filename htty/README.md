# htty - A fork of [ht](https://github.com/andyk/ht)

`htty` controls processes that are attached to a headless terminal.
It has both a command line interface, and a Python API.

## Components

This repo includes two packages. It was necesssary to split them up because [Maturin refuses](https://github.com/PyO3/maturin/discussions/2683) to build packages with both rust binaries and python console scripts. `htty-core` got the rust binary, `htty` got the pyton API and the console script.

- **[htty](../README.md)** - You're viewing the README for this one. It contains the user-facing parts. It is packaged as a pure python source distribution.
- **[htty-core](../htty-core/README.md)** - Contains the `ht` binary (built by [maturin](https://github.com/PyO3/maturin)) and a minimal python interface for running it.  It's packaged as an architecture-specific wheel.

`htty` depends on `htty-core`.
It was necesssary to split them up because [Maturin objects](https://github.com/PyO3/maturin/blob/a50defe91c2c779d7f9aedb2ac0a788286f45ae8/src/build_context.rs#L1066) to building packages with both rust binaries and python console scripts.
`htty-core` got the rust binary, `htty` got the pyton API and the console script.

For more about the project in general check out [the README at the repo root](https://github.com/MatrixManAtYrService/htty) or [the docs](https://matrixmanatyrservice.github.io/htty/htty.html) instead.
