# uv2nix-based pytest devshell that tests the exact htty-pylib environment
{ pkgs, inputs, system, perSystem, ... }:

let
  # Get the exact htty-pylib environment that we're exporting
  httyPylib = perSystem.self.htty-pylib;

  # Load the test workspace to get pytest and test dependencies
  testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../tests;
  };

  # Create python set with ONLY test dependencies (no htty - that comes from htty-pylib)
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (testWorkspace.mkPyprojectOverlay { 
        sourcePreference = "wheel";
      })
    ]
  );

  # Create environment with test dependencies (pytest, etc.)
  # Remove htty from deps since we get it from htty-pylib
  testDepsOnly = builtins.removeAttrs testWorkspace.deps.default [ "htty" ];
  testDepsEnv = pythonSet.mkVirtualEnv "test-deps-only" testDepsOnly;

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
    # The exact htty environment we're testing
    httyPylib
    
    # Test dependencies (pytest, etc.) 
    testDepsEnv
    
    # Additional test tools
    testVim
    
    # Development tools for debugging
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
    echo "Testing htty-pylib: ${httyPylib}"
    echo "With test tools: ${testDepsEnv}"
    echo ""
    echo "Available commands:"
    echo "  pytest        - Run tests directly"
    echo "  python        - Python with htty + test tools"
    echo ""
    echo "Example usage:"
    echo "  pytest tests/lib_tests/test_htty.py::test_hello_world_with_scrolling -v -s"
    echo "  pytest tests/lib_tests/ -v"
    echo ""
    
    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"
    
    # Set up Python path to include both environments
    # htty-pylib first (priority), then test deps
    export PYTHONPATH="${httyPylib}/lib/python3.12/site-packages:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"
    
    # Set up PATH to include both environments
    export PATH="${httyPylib}/bin:${testDepsEnv}/bin:$PATH"
  '';
}