# Generic code analysis tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage trimWhitespaceCheck makeGenerateConstantsCheck;

  # Create the constants generation check with file list
  generateConstantsCheck = makeGenerateConstantsCheck {
    inherit flake;
    files = [
      "htty-core/src/rust/constants.rs"
      "htty/src/htty/constants.py"
    ];
  };
in
createAnalysisPackage {
  name = "generic-analysis";
  description = "Generic code analysis";
  checks = {
    trim-whitespace = trimWhitespaceCheck;
    generate-constants = generateConstantsCheck;
  };
}
