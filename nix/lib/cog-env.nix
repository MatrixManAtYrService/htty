# Shared environment variables for Cog tool configuration
# Used by both codegen.nix and version-bump.nix to ensure consistency
{ pkgs }:

let
  version = import ./version.nix { inherit pkgs; };
in {
  HTTY_VERSION = version.version;
  HTTY_COMMON_RUFF_TOML = builtins.readFile ../../common/ruff.toml;
  HTTY_COMMON_PYRIGHT_TOML = builtins.readFile ../../common/pyright.toml;
}