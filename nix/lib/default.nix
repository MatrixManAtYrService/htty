# Simple re-export of individual lib modules
# This allows flake.lib.checks.fastChecks to mirror lib/checks.nix structure
{ inputs, flake, ... }:

# Return a function that takes pkgs and returns the lib modules
pkgs: {
  pypkg = (import ./pypkg.nix { inherit inputs; }) pkgs;
  testcfg = (import ./testcfg.nix { inherit inputs; }) pkgs;
  checks = import ./checks.nix pkgs;
  constants = import ./constants.nix { inherit pkgs; };
  version = import ./version.nix { inherit pkgs; };
  cogEnv = import ./cog-env.nix { inherit pkgs; };
} // (import ./pytest-shell.nix { inherit inputs; }) pkgs
