# Cross-compiled htty-core wheel for aarch64-linux from x86_64-linux
{ inputs, pkgs, ... }:

let
  # Use nixpkgs with cross-compilation
  crossPkgs = import inputs.nixpkgs {
    system = "x86_64-linux";
    crossSystem = {
      config = "aarch64-unknown-linux-gnu";
    };
  };
in
crossPkgs.callPackage ./htty-core-wheel.nix { inherit inputs; }
