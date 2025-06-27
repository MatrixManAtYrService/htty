# Pure pytest devshell with no additional packages
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;
  
  # No packages - pure pytest environment
  packages = [];
}
