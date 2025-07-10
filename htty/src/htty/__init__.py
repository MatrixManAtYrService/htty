"""
htty - a wrapper around [ht](https://github.com/andyk/ht)

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

# Library Usage

The `terminal_session` context manager yields a `HtWrapper` object which has methods for communicating with the underlying `ht` process.

```python
from htty import Press, terminal_session

# start an interactive bourne shell in a small headless terminal
with terminal_session("sh -i", rows=4, cols=6) as sh:

    # print enough so that the prompt is at the bottom of the screen
    sh.send_keys([r"printf '\\n\\n\\n\\nhello world\\n'", Press.ENTER])
    sh.expect("world")
    hello = sh.snapshot()

    # clear the terminal
    sh.send_keys(["clear", Press.ENTER])
    sh.expect_absent("world")
    sh.expect("\\$")
    cleared = sh.snapshot()

# assert correct placement
assert hello.text == '\\n'.join([
    "      ", # line wrap after 6 chars
    "hello ",
    "world ",
    "$     ", # four rows high
])

# assert that clear... cleared
assert cleared.text == '\\n'.join([
    "$     ",
    "      ",
    "      ",
    "      ",
])
```
It's a good idea to `expect` something before you take a snapshot, otherwise the snapshot might happen before the child process has fully arrived at the state you're trying to capture.

# Command Line Usage

Unlike the library, the `htty` command accepts all of its instructions before it starts.
It will run them all, terminate the child process, and exit.

If you're looking for something more interactive, consider running `ht` instead of `htty`.

```
$ htty --help
# DOCS_OUTPUT: htty --help
```

The `sl` command animates an ascii-art train engine driving from right to left across your terminal.
Near the middle of the engine are some `I`'s an further back is a `Y`.
`htty` can use the appearance and dissapearance of these characters to trigger snapshots of the train.

The command below wraps `sl`, and captures two snapshots (triggered by Y appearing and I dissapering).
 ints them to stdout with a '----' to indicate the end of each snapshot.

```
$ htty -r 15 -c 50 --expect Y --snapshot --expect-absent I --snapshot -- sl

                    (@@@)
                 ====        ________
             _D _|  |_______/        \\__I_I_____==
              |(_)---  |   H\\________/ |   |
              /     |  |   H  |  |     |   |
             |      |  |   H  |__-----------------
             | ________|___H__/__|_____/[][]~\\____
             |/ |   |-----------I_____I [][] []  D
           __/ =| o |=-~~\\  /~~\\  /~~\\  /~~\\ ____Y
            |/-=|___|=   O=====O=====O=====O|_____
             \\_/      \\__/  \\__/  \\__/  \\__/



----


      ___________
_===__|_________|
     =|___ ___|      _________________
      ||_| |_||     _|                \\_____A
------| [___] |   =|                        |
______|       |   -|                        |
  D   |=======|____|________________________|_
__Y___________|__|__________________________|_
___/~\\___/          |_D__D__D_|  |_D__D__D_|
   \\_/               \\_/   \\_/    \\_/   \\_/



----
```
Warning: if you don't include an `--expect`, it's likely that your first snapshot will be empty because it happens before the command can get around to producing any output.
"""

import htty.keys as keys
from htty.ht import (
    HtWrapper,
    ProcessController,
    SnapshotResult,
    run,
    terminal_session,
)
from htty.keys import Press

__all__ = ["terminal_session", "run", "HtWrapper", "ProcessController", "SnapshotResult", "Press", "keys"]
