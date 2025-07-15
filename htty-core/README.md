# htty - A fork of [ht](https://github.com/andyk/ht)

`htty` controls processes that are attached to a headless terminal.
It has both a command line interface, and a Python API.

## Components

This repo includes two packages. It was necesssary to split them up because [Maturin refuses](https://github.com/PyO3/maturin/discussions/2683) to building packages with both rust binaries and python console scripts. `htty-core` got the rust binary, `htty` got the pyton API and the console script.

- **[htty](../README.md)** - You're viewing the README for this one.  It contains both the `htty` command, and the `htty` python library.  It is packaged as a pure python source distribution.
- **[htty-core](../htty-core/README.md)** You're viewing the README for this one.  It Contains the `ht` binary (built by [maturin](https://github.com/PyO3/maturin)) and a minimal python interface for running it.  It's packaged as an architecture-specific wheel.



For more about the project in general check out [the README at the repo root](https://github.com/MatrixManAtYrService/htty) or [the docs](https://matrixmanatyrservice.github.io/htty/htty.html) instead.
