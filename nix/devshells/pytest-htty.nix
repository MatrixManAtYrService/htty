# Pytest devshell for testing htty package
{ flake, inputs, system, perSystem, ... }:

let
  pkgs = inputs.nixpkgs.legacyPackages.${system};
  lib = flake.lib pkgs;
  inherit (lib.testcfg) testVim;
in

lib.makePytestShell {
  inherit pkgs system perSystem;

  # Use the complete htty environment
  packages = [ perSystem.self.htty ];

  extraBuildInputs = [ testVim ];
  extraShellHook = ''
    # Set vim target for tests
    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"

    # Make htty path available for tests
    export HTTY_PATH="${perSystem.self.htty}"

    # Add htty bin to PATH (for both ht binary and htty command access)
    export PATH="${perSystem.self.htty}/bin:$PATH"
  '';
}
