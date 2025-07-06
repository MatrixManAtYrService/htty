# Pytest devshell for testing htty-core-wheel package
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the htty-core-wheel package for verification
  packages = [ perSystem.self.htty-core-wheel ];

  extraShellHook = ''
    # Make htty-core-wheel output available for tests
    export HTTY_CORE_WHEEL_PATH="${perSystem.self.htty-core-wheel}"
  '';
}
