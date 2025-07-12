// Auto-generated constants from nix/lib/constants.nix
// DO NOT EDIT THE GENERATED SECTIONS MANUALLY

//[[[cog
// import os
// default_cols = int(os.environ['HTTY_DEFAULT_COLS'])
// default_rows = int(os.environ['HTTY_DEFAULT_ROWS'])
//]]]
//[[[end]]]

// Terminal configuration
/*[[[cog
cog.outl(f"pub const DEFAULT_TERMINAL_COLS: u16 = {default_cols};")
cog.outl(f"pub const DEFAULT_TERMINAL_ROWS: u16 = {default_rows};")
]]]*/
pub const DEFAULT_TERMINAL_COLS: u16 = 60;
pub const DEFAULT_TERMINAL_ROWS: u16 = 30;
//[[[end]]]