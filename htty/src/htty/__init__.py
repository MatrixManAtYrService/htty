"""
htty - a wrapper around [ht](https://github.com/andyk/ht)

Run a command in a headless terminal of indicated size.
Send keystrokes and take snapshots.

# Library Usage

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

The comand below asks for two snapshots.
They're printed to stdout with a '----' to indicate the end of each snapshot.

```
$ htty -r 20 -c 50 --expect Q --snapshot --snapshot -- aafire


                       :|i=.
                      .|nZXI=
                       .=vXZXI:
                         -I#:WWn=
                         -nW;==Q#|
                        .IW===;QWS-.
                        =XQ;QW#Z#X|.
                 :||:  :S#W#Xi+IX#S|.
                iW==WXIn:Q;WSi++IXS|.. .
..             -X;+|=;::Q=|++==QZZn+.            .
WQI            .IW==Q#XZQ+|+|i::||QZSSv:         |
==Z        :nZXiS;||+Q:Q;=QZ#|vnvi=QQ;=#n+--.    -
IWS  .=-  -#QQ::;|lvll::|=:Z;|Iv:|QW;==;W#I=.
-:----:-.-S;=::W=iii:vooI|+=|vvi=n:iW===;WS++-   |
#. W,;iSWQ#Z#;+||i||v=X=ni|=|vvv:=QX=||||QWZn=.  X
==.n;+vW==:-|Z+||ill+vXmmuQ=ivvn=l=+|::|+==;Z=--.
-+|SnS~:||t#IS:(=:vn#]wmWf;Q)nv==(:|ilvii=++ZS:S .
) )  ==t`W`WW WW^tW--'?-`~-`Wt''---`'^-^`^`Zt+t :
----





                      -+++-
                     -I#:W#S+-
                     -|X:;==QWSI=.
                   -=v#=+|ii|+;WX=.
                -+vnZW=|lll::|+Q:v=.
              =nZ##Z:Q=|i::ll:|:ZSnI-
 .      :-    SWQWWW;+|:lIIvl:+WXZ:#i:.
       -I+    SQ=|=;;+:Ivv:l:i=##QQ#i::.
       =nn|- .nQ|ii+QQ==+====Q:Q==Q#IvXS|.
      .:IvnSSnZQ|i::||||||=QZZW+||===|QW#S:.
    --:i|-IQ|+++ilv::vvn:|=||=;|lI||i+:ZZni-
-  =yvIZn=n=::|iIvvl:n==l=+:v>=|lv+^+WQ:::XI-    :
=  i:QQQ=Q#QW+vnnn:W<d#X(QZvI+:v==-.+vQWnSX#X++-.-
..-|v:==+=:= (nnvnvn=mmm=+Q][ =nX[-=n#=Qvv:WQiZv.=
. )  .= WW tWWW ^^^-t--^`-^t-+W``W-W^`t'^ WWtt=::.
----
```
Without a `--expect`, it's likely that your first snapshot will be empty because it happens before the command can get around to producing any output.
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
