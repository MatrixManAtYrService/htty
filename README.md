# htty - A fork of [ht](https://github.com/andyk/ht)

[![CI](https://github.com/MatrixManAtYrService/htty/workflows/Test/badge.svg)](https://github.com/MatrixManAtYrService/htty/actions/workflows/tests.yml)
[![PyPI htty](https://img.shields.io/pypi/v/htty.svg)](https://pypi.org/project/htty/)
[![PyPI python versions](https://img.shields.io/pypi/pyversions/htty.svg)](https://pypi.org/project/htty/)


`htty` runs commands in a headless terminal.
To interact with that terminal programatically, you can use either its CLI or its Python API.

For details, see the [docs](https://matrixmanatyrservice.github.io/htty/htty.html).

### Example

First, lets run `sl` normally.
It will [animate an ascii train in our terminal](https://linuxcommandlibrary.com/man/sl).

Then we'll use `htty` to run `sl`.
It accepts instructions about when it should dump snapshots of the headless terminal.

![animated ascii-art train](example.svg)

```
htty -r 12 -c 50 --expect Y --snapshot --expect-absent I --snapshot -- sl
```
- run `sl` in a 12x50 headless terminal
- capture two snapshots:
   - after the first `Y` appears
   - after the last `I` dissapears

### Python API

The python code below walks `vim` through a short flow, capturing snapshots along the way.

```python3
from htty import Press, terminal_session

with terminal_session("vim", rows=20, cols=50) as vim:
    vim.expect("version 9.1.1336")  # wait for vim to draw startup screen
    startup = vim.snapshot()

    vim.send_keys("i")              # enter insert mode
    vim.send_keys("hello world")
    vim.send_keys(Press.ESCAPE)     # exit insert mode
    vim.expect_absent("INSERT")     # wait for vim to exit insert mode
    hello = vim.snapshot()

improved_line = next(
    line for line in startup.text.splitlines() if "IMproved" in line
)
assert improved_line == "~               VIM - Vi IMproved                 "

assert hello.text.split("\n")[0].strip() == "hello world"
```

The `expect` commands are useful to prevent race conditions.
Without them we're likely to take a snapshot before vim has fully arrived at the expected state.

### Command Line Interface

This command is equivalent to the python code above.
The arguments are processed in order.
The snapshots are printed to stdout, and are terminated by a '----' .

```bash
$ htty --rows 20 --cols 50 \
  --expect 'version 9.1.1336' --snapshot \
  --keys 'i,hello world,Escape' \
  --expect-absent INSERT --snapshot \
  -- vim
```
```
~
~
~
~               VIM - Vi IMproved
~
~                version 9.1.1336
~            by Bram Moolenaar et al.
~  Vim is open source and freely distributable
~
~            Sponsor Vim development!
~ type  :help sponsor<Enter>    for information
~
~ type  :q<Enter>               to exit
~ type  :help<Enter>  or  <F1>  for on-line help
~ type  :help version9<Enter>   for version info
~
~
~
                                0,0-1         All
----
hello world
~
~
~
~
~
~
~
~
~
~
~
~
~
~
~
~
~
~
                                1,11          All
----
```

## Usage

The `htty` package [on pypi](https://pypi.org/project/htty/) installs both the CLI and the Python API:
```
$ pip install htty

$ htty -r 4 -c 4 --expect d --snapshot -- echo hello world
hell
o wo
rld

----

$ python -c 'from htty import terminal_session
with terminal_session("echo hello world", rows=4, cols=4) as hello:
    hello.expect("d")
    s = hello.snapshot()
    print(s.text)
'
hell
o wo
rld

```

Nix users can reference the CLI directly via the `#htty-cli` flake output:
```
$ nix run github:MatrixManAtYrService/htty#htty-cli -- -r 4 -c 4 --expect d --snapshot -- echo hello world
hell
o wo
rld

----
```

Nix users can also use the `#htty` output, which has both the cli and the python library. (These are separate so that CLI-only users have the option of leaving their PYTHONPATH untouched.):

```
$ nix shell github:MatrixManAtYrService/htty#htty

(nix-shell) $ htty -r 4 -c 4 --expect d --snapshot -- echo hello world
hell
o wo
rld

----

(nix-shell) $ python -c 'from htty import terminal_session
with terminal_session("echo hello world", rows=4, cols=4) as hello:
    hello.expect("d")
    s = hello.snapshot()
print(s.text)'
hell
o wo
rld

```

## Package Architecture

This project uses a two-package distribution. `htty` depends on `htty-core`.

- **[htty](htty/README.md)** - Install this. It provides `htty` both as a command-line tool and as a python library.  It's pure python, packaged as a source distribution.
- **[htty-core](htty-core/README.md)** - Contains the `ht` binary (written in rust, modified by this fork, built by [maturin](https://github.com/PyO3/maturin)) and a minimal python interface for running it.  It's packaged as an architecture-specific wheel.
