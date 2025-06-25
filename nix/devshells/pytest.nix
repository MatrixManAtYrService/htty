{ pkgs, inputs, system, perSystem, ... }:

let
  # Get the test environment package
  httyTest = perSystem.self.htty-test;
  
  # Get overlays for Rust (if needed for debugging)
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit system; 
    inherit overlays; 
  };
  
  # Get test vim from lib using Blueprint pattern
  lib = inputs.self.lib pkgs;
  inherit (lib.testcfg) testVim;
in
pkgsWithRust.mkShell {
  buildInputs = with pkgsWithRust; [
    # Test environment (includes pytest and htty-pylib)
    httyTest
    
    # Additional test tools
    testVim
    
    # Development tools for debugging
    python3
    uv
    ruff
    
    # Nix tools
    nixpkgs-fmt
    nil
  ] ++ pkgsWithRust.lib.optionals pkgsWithRust.stdenv.isDarwin [
    pkgsWithRust.libiconv
    pkgsWithRust.darwin.apple_sdk.frameworks.Foundation
  ];

  shellHook = ''
    echo "🧪 htty pytest environment ready!"
    echo ""
    echo "Available commands:"
    echo "  htty-test         - Run basic functionality tests"
    echo "  htty-pytest       - Run pytest with htty environment"
    echo "  htty-test-python  - Python shell with htty + test tools"
    echo ""
    echo "Example usage:"
    echo "  htty-pytest lib_tests/test_htty.py::test_hello_world_with_scrolling"
    echo "  htty-pytest lib_tests/"
    echo ""
    
    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"
    
    # Make sure the test environment is properly set up
    export PATH="${httyTest}/bin:$PATH"
  '';
}