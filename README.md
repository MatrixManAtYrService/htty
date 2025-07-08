# htty - A fork of [ht](https://github.com/andyk/ht)

![CI](https://github.com/MatrixManAtYrService/htty/workflows/CI/badge.svg)

Some terminal applications don't make it easy to capture their output in a human-readable way.
Here's vim's startup screen:

```
~                       VIM - Vi IMproved
~                       version 9.1.1336
~                   by Bram Moolenaar et al.
~          Vim is open source and freely distributable
~
~                 Help poor children in Uganda!
```

If you capture vim's ouput directly, you won't get the nicely formatted text you see above.
Instead, you'll get raw ANSI escape sequences.

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;32HHelp poor children in Uganda!
```

htty connects vim (or any other process) to a [pseudoterminal interface](https://man7.org/linux/man-pages/man7/pty.7.html)) which directs output to an ANSI interpreter.
Most ANSI interpreters are bundled into terminals that put characters on your screen for viewing, but this one is headless, so instead the text is stored internally for later reference.

This is useful if you want to work with program output as a human-readable string without having a human in the loop.




### Python API

The python code below walks `vim` through a short flow, capturing snapshots along the way.

The `expect` commands are useful to prevent race conditions.
Without them we're likely to take a snapshot before vim has fully arrived at the expected state.


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

### Command Line Interface

This command is equivalent to the python code above.
The arguments are processed in order.
The snapshots are printed to stdout, and are terminated by a '----' .

```bash
$ htty --rows 20 --cols 50 \
  --expect 'version 9.1.1336' --snapshot \
  --keys 'i,hello world,Escape' --expect-absent INSERT \
  --snapshot \
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
- **[htty-core](htty-core/README.md)** - Contains an `ht` binary (modified in this fork) and a minimal python interface for interacting with it.  It's packaged as an architecture-specific wheel.  `htty` depends on `htty-core`.
