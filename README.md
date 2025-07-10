# htty - A fork of [ht](https://github.com/andyk/ht)


`htty` runs commands with a headless terminal attached.
It can be configured to provide snapshots when patterns appear.

### Example

The [sl](https://linuxcommandlibrary.com/man/sl) command provides an ascii animated train for your terminal.

![animated ascii-art train](example.svg)

Here we ran `sl` with `htty`.
We'll took one snapshot when a `Y` is seen, and another when the last `I` has gone away.

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

## Package Architecture

This project uses a two-package distribution:

- **[htty](htty/README.md)** - Install this. It provides `htty` both as a command-line tool and as a python library.  It's pure python, packaged as a source distribution.
- **[htty-core](htty-core/README.md)** - Contains the `ht` binary (written in rust, modified by this fork, built by [maturin](https://github.com/PyO3/maturin)) and a minimal python interface for running it.  It's packaged as an architecture-specific wheel.  `htty` depends on `htty-core`.

## Docs

For more information, see [the docs](./docs/htty.html).
