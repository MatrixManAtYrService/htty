# Generic code analysis tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage trimWhitespaceCheck;
in
createAnalysisPackage {
  name = "generic-analysis";
  description = "Generic code analysis";
  checks = {
    trim-whitespace = trimWhitespaceCheck;
  };
}
