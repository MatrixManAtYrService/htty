# Code generation tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage trimWhitespaceCheck makeGenerateConstantsCheck makeGenerateVersionCheck;

  # propagate constants from ../lib/constants.nix
  generateConstantsCheck = makeGenerateConstantsCheck {
    inherit flake;
    files = [
      "htty-core/src/rust/constants.rs"
      "htty-core/src/python/htty_core/constants.py"
      "htty/src/htty/constants.py"
    ];
  };

  # propagate versions from ../lib/version.nix
  generateVersionCheck = makeGenerateVersionCheck {
    inherit flake;
    files = [
      "htty-core/Cargo.toml"
      "htty-core/pyproject.toml"
      "htty/pyproject.toml"
      "htty-core/src/rust/cli.rs"
      "htty/src/htty/cli.py"
      "htty/src/htty/__init__.py"
      "htty-core/src/python/htty_core/__init__.py"
    ];
  };
in
createAnalysisPackage {
  name = "codegen";
  description = "Code generation";
  checks = {
    trim-whitespace = trimWhitespaceCheck;
    generate-constants = generateConstantsCheck;
    generate-version = generateVersionCheck;
  };
}
