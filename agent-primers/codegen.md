# Code Generation with Cog

## Overview

The htty project uses [Cog](https://nedbatchelder.com/code/cog/) for automated code generation to maintain consistency across multiple languages (Rust, Python) and file formats (TOML, source files). This ensures that constants and version information stay synchronized throughout the codebase.

## Architecture

### Central Source Files

The code generation system is driven by two central Nix files that serve as the single source of truth:

#### 1. `nix/lib/version.nix` - Version Management
Contains all version-related information for the project:

```nix
{
  major = 0;
  minor = 2;
  patch = 1;
  prerelease = "dev202507140024"; # Python-compatible format: dev + YYYYMMDDHHMM

  # Synthesized versions
  version = "0.2.1-dev202507140024";
  versionWithGit = "0.2.1-dev202507140024+a1b2c3d4";

  # Package-specific formats
  cargo.version = "0.2.1-dev202507140024";    # For Rust Cargo.toml
  python.version = "0.2.1-dev202507140024";   # For Python pyproject.toml
}
```

**Key Features:**
- Single source of truth for all version information
- Automatic git SHA integration
- Python PEP 440 compatible prerelease format
- Package-specific version formatting

#### 2. `nix/lib/constants.nix` - Project Constants
Contains all shared constants used across the codebase:

```nix
{
  terminal = {
    default_cols = 60;
    default_rows = 30;
  };

  timing = {
    default_sleep_after_keys_ms = 100;
    coordination_delay_ms = 200;
    default_exit_timeout_ms = 5000;
    # ... many more timing constants
  };

  buffers = {
    read_buf_size = 131072;
    channel_buffer_size = 1024;
    # ... buffer sizes
  };
}
```

**Key Features:**
- Centralized configuration for the entire project
- Language-agnostic constant definitions
- Comprehensive documentation with usage references
- Consistent naming conventions

### Code Generation Process

The generation process is orchestrated by `nix/packages/codegen.nix`, which defines:

1. **Files to Process**: Lists all files that contain Cog blocks
2. **Environment Setup**: Converts Nix constants to environment variables
3. **Execution**: Runs Cog to regenerate code blocks

## Cog Block Patterns

### Environment Variable Setup Block

Used to import constants from Nix environment variables:

```rust
//[[[cog
// import os
// default_cols = int(os.environ['HTTY_DEFAULT_COLS'])
// default_rows = int(os.environ['HTTY_DEFAULT_ROWS'])
// # ... more variable imports
//]]]
//[[[end]]]
```

**Purpose**: Loads constants from environment variables into Cog variables for use in generation blocks.

### Code Generation Block

Used to generate actual code using the imported constants:

```rust
/*[[[cog
cog.outl(f"pub const DEFAULT_TERMINAL_COLS: u16 = {default_cols};")
cog.outl(f"pub const DEFAULT_TERMINAL_ROWS: u16 = {default_rows};")
]]]*/
pub const DEFAULT_TERMINAL_COLS: u16 = 60;
pub const DEFAULT_TERMINAL_ROWS: u16 = 30;
//[[[end]]]
```

**Purpose**: Generates the actual code that gets compiled/executed. The content between the block markers is automatically updated.

### Version Block (Simple)

For simple version insertion:

```toml
# [[[cog
# import os
# cog.out(f'version = "{os.environ["HTTY_VERSION"]}"')
# ]]]
version = "0.2.1-dev202507140024"
# [[[end]]]
```

**Purpose**: Inserts version strings into configuration files.

## File Types and Patterns

### Rust Files (`*.rs`)

**Comments**: Use `//` and `/**/` comment styles
**Pattern**: Import environment variables, then generate constants
**Example files**:
- `htty-core/src/rust/constants.rs` - Project constants
- `htty-core/src/rust/cli.rs` - Version info for `--version` flag

### Python Files (`*.py`)

**Comments**: Use `#` comment style
**Pattern**: Similar to Rust but with Python syntax
**Example files**:
- `htty/src/htty/constants.py` - Project constants
- `htty/src/htty/cli.py` - Version info for `--version` flag
- `htty/src/htty/__init__.py` - Module version

### Configuration Files (`*.toml`)

**Comments**: Use `#` comment style
**Pattern**: Simple version insertion, no complex logic
**Example files**:
- `htty-core/Cargo.toml` - Rust package version
- `htty-core/pyproject.toml` - Python package version (htty-core)
- `htty/pyproject.toml` - Python package version (htty)

## Running Code Generation

### Manual Generation

```bash
# Generate all files
nix run .#codegen

# Generate only constants
nix run .#generate-constants

# Generate only versions
nix run .#generate-version
```

### Automatic Generation

Code generation runs automatically as part of:
- `./steps.sh` - Full development workflow
- CI/CD pipeline - Ensures consistency in builds
- Pre-commit hooks (if configured)

## Environment Variable Mapping

The Nix build system automatically converts constants to environment variables:

| Nix Path | Environment Variable | Example Value |
|----------|---------------------|---------------|
| `version.version` | `HTTY_VERSION` | `"0.2.1-dev202507140024"` |
| `version.versionInfo.htty` | `HTTY_VERSION_INFO_HTTY` | `"htty 0.2.1-dev202507140024 (a1b2c3d4)"` |
| `terminal.default_cols` | `HTTY_DEFAULT_COLS` | `"60"` |
| `timing.coordination_delay_ms` | `HTTY_COORDINATION_DELAY_MS` | `"200"` |

## Generated File Structure

### Constants Files

**Rust**: `htty-core/src/rust/constants.rs`
```rust
// Terminal configuration
pub const DEFAULT_TERMINAL_COLS: u16 = 60;
pub const DEFAULT_TERMINAL_ROWS: u16 = 30;

// Timing constants as Duration values
pub const COORDINATION_DELAY: Duration = Duration::from_millis(200);
```

**Python**: `htty/src/htty/constants.py`
```python
# Terminal configuration
DEFAULT_TERMINAL_COLS = 60
DEFAULT_TERMINAL_ROWS = 30

# Timing constants (milliseconds)
COORDINATION_DELAY_MS = 200
```

### Version Files

**Cargo.toml**:
```toml
[package]
name = "htty_core"
version = "0.2.1-dev202507140024"
```

**Python __init__.py**:
```python
__version__ = "0.2.1-dev202507140024"
```

## Important Guidelines

### Do NOT Edit Generated Sections

Generated content is between Cog markers:
```
//[[[cog ... ]]] or /*[[[cog ... ]]]*/
// Generated content here - DO NOT EDIT
//[[[end]]]
```

**Always edit the source Nix files instead:**
- Edit `nix/lib/version.nix` for version changes
- Edit `nix/lib/constants.nix` for constant changes
- Run `nix run .#codegen` to regenerate

### Avoiding Cog Conflicts

**Problem**: Type annotations with nested brackets can confuse Cog:
```python
# This breaks Cog because it ends with ]]]
actions: list[tuple[str, Optional[str]]] = []
```

**Solution**: Use type aliases:
```python
# At module level
ActionTuple: TypeAlias = tuple[str, Optional[str]]

# In function
actions: list[ActionTuple] = []
```

### Version Format Requirements

**Python**: Must follow PEP 440
- ✅ `0.2.1-dev202507140024` (prerelease with timestamp)
- ✅ `0.2.1` (stable release)
- ❌ `0.2.1-2025-July-14-00-24` (month names not allowed)

**Rust**: More flexible, but we use same format for consistency

### Environment Variable Access

In Cog blocks, access constants via `os.environ`:
```python
# [[[cog
# import os
# version = os.environ["HTTY_VERSION"]
# default_cols = int(os.environ["HTTY_DEFAULT_COLS"])
# ]]]
```

## Adding New Constants

1. **Add to `nix/lib/constants.nix`**:
```nix
new_section = {
  new_constant = 42;
  another_constant = "hello";
};
```

2. **Update target files** with Cog blocks:
```rust
/*[[[cog
new_constant = int(os.environ['HTTY_NEW_CONSTANT'])
cog.outl(f"pub const NEW_CONSTANT: i32 = {new_constant};")
]]]*/
//[[[end]]]
```

3. **Register file in `nix/packages/codegen.nix`**:
```nix
generateConstantsCheck = makeGenerateConstantsCheck {
  files = [
    "path/to/your/new/file.rs"
    # ... existing files
  ];
};
```

4. **Regenerate**:
```bash
nix run .#codegen
```

## Adding New Versioned Files

1. **Add Cog blocks to your file**:
```python
# [[[cog
# import os
# cog.out(f'__version__ = "{os.environ["HTTY_VERSION"]}"')
# ]]]
__version__ = "0.2.1-dev202507140024"
# [[[end]]]
```

2. **Register in `nix/packages/codegen.nix`**:
```nix
generateVersionCheck = makeGenerateVersionCheck {
  files = [
    "path/to/your/new/file.py"
    # ... existing files
  ];
};
```

3. **Regenerate**:
```bash
nix run .#codegen
```

## Integration with CI/CD

The CI workflow automatically:
1. Runs `nix run .#codegen` to ensure all generated code is up-to-date
2. Fails the build if generated content is out of sync with source
3. Uses the same constants and versions for building packages

This ensures that what you test locally matches what gets built and deployed.

## Benefits

1. **Single Source of Truth**: All constants and versions defined in one place
2. **Cross-Language Consistency**: Same values across Rust, Python, and config files
3. **Type Safety**: Generate appropriate types for each language (Duration for Rust, int for Python)
4. **Documentation**: Constants include usage references and descriptions
5. **Automation**: No manual synchronization needed
6. **CI Integration**: Automatic validation that generated code is current

This system eliminates the common problem of constants getting out of sync across different parts of a multi-language codebase.