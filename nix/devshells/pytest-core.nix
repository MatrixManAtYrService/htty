# pytest devshell with htty-core (Rust + minimal Python bindings)
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the htty-core environment (maturin-built wheel)
  packages = [ perSystem.self.htty-core-env ];
}
