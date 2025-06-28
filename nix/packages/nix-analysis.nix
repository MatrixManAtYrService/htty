# Nix code analysis tools
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) createAnalysisPackage deadnixCheck nixpkgsFmtCheck statixCheck;
in
createAnalysisPackage {
  name = "nix-analysis";
  description = "Nix code analysis";
  checks = {
    deadnix = deadnixCheck;
    nixpkgs-fmt = nixpkgsFmtCheck;
    statix = statixCheck;
  };
}
