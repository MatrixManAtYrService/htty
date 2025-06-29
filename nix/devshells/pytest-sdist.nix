# uv2nix-based pytest devshell for pure Python unit tests (no ht binary)
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the pure Python htty environment (no binary)
  packages = [ perSystem.self.htty-py-sdist ];

  # Add pyright for type checking
  extraBuildInputs = [ pkgs.pyright ];
}
