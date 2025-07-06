# Pytest devshell for testing htty-sdist package
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the htty-sdist package for verification
  packages = [ perSystem.self.htty-sdist ];

  extraShellHook = ''
    # Make htty-sdist output available for tests
    export HTTY_SDIST_PATH="${perSystem.self.htty-sdist}"
  '';
}
