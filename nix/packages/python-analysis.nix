# Python code analysis tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage ruffCheckCheck ruffFormatCheck;
in
createAnalysisPackage {
  name = "python-analysis";
  description = "Python code analysis";
  checks = {
    ruff-check = ruffCheckCheck;
    ruff-format = ruffFormatCheck;
  };
}
