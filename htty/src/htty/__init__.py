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

htty makes it possible to get a human-friendly string representing the contents of a terminal, without having an actual graphical terminal emulator in the loop.

To do this, it connects processes (like vim) to a [pseudoterminal interface](https://man7.org/linux/man-pages/man7/pty.7.html) which directs output to an ANSI interpreter.
Most ANSI interpreters are involved with putting characters on a screen for humans to view directly, but this one is headless, so the text is stored internally for later reference.

htty lets you control the underlying process and take snapshots of the headless terminal's contents at times when you expect it to be interesting.
This can be handy for testing, like when you want to assert that the user's terminal looks a certain way, or for when you're expecting large subprocess output and you want to show your user only a certain part of it.
(This can be especially useful if your user is an AI and you're being charged per-token.)

It's a bit like a zoomed-out grep:
Instead of finding lines of a file, it finds snapshots of a terminal session.

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

Unlike the `htty` python library, the `htty` command accepts all of its instructions before it starts.
It will do the following:

1. run all instruction, printing snapshots along the way
2. terminate the child process
3. exit

If you're looking for something that doesn't clean the process up afterwards, consider one of these:
 - run  [ht](https://github.com/andyk/ht?tab=readme-ov-file#usage) of `htty`
 - use `htty` as a python library
 - other terminal emulator libraries such as [pyte](https://github.com/selectel/pyte)

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

# [[[cog
# import os
# cog.out(f'__version__ = "{os.environ["HTTY_VERSION"]}"')
# ]]]
__version__ = "0.2.27"
# [[[end]]]

__all__ = [
    "terminal_session",
    "run",
    "HtWrapper",
    "ProcessController",
    "SnapshotResult",
    "Press",
    "keys",
    "__version__",
]
