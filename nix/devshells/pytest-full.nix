# uv2nix-based pytest devshell that tests the exact htty-pylib environment
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};

  # Get test vim from lib using Blueprint pattern
  lib = flake.lib pkgs;
  inherit (lib.testcfg) testVim;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the complete htty environment (with binary and Python wrapper)
  packages = [ perSystem.self.htty ];

  # Wheel-specific additions
  extraBuildInputs = [ testVim ];
  extraShellHook = ''
    # Set vim target for tests
    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"

    # Add htty bin to PATH (for both ht binary and htty command access)
    export PATH="${perSystem.self.htty}/bin:$PATH"
  '';
}
