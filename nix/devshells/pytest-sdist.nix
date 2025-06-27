# uv2nix-based pytest devshell for pure Python unit tests (no ht binary)
{ pkgs, inputs, system, perSystem, ... }:

let
  # Get the pure Python htty environment (no binary)
  httyPySdist = perSystem.self.htty-py-sdist;

  # Load the test workspace to get pytest and test dependencies
  testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../tests;
  };

  # Create python set with ONLY test dependencies (no htty - that comes from htty-py-sdist)
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
  # Remove htty from deps since we get it from htty-py-sdist
  testDepsOnly = builtins.removeAttrs testWorkspace.deps.default [ "htty" ];
  testDepsEnv = pythonSet.mkVirtualEnv "test-deps-only" testDepsOnly;

  # Get overlays for any additional tools
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs { 
    inherit system; 
    inherit overlays; 
  };

in
pkgsWithRust.mkShell {
  buildInputs = with pkgsWithRust; [
    # Pure Python htty environment (no ht binary)
    httyPySdist
    
    # Test dependencies (pytest, etc.) 
    testDepsEnv
    
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
    echo "🧪 htty pytest-sdist environment ready!"
    echo ""
    echo "Pure Python htty (source distribution): ${httyPySdist}"
    echo "With test tools: ${testDepsEnv}"
    echo ""
    echo "⚠️  NOTE: ht binary is NOT available in this environment"
    echo "   This is intentional for unit testing Python code in isolation"
    echo ""
    echo "Available commands:"
    echo "  pytest        - Run unit tests directly"
    echo "  python        - Python with htty + test tools (no ht binary)"
    echo ""
    echo "Example usage:"
    echo "  pytest -vs -m sdist  # Run sdist-marked tests"
    echo "  pytest tests/py_unit_tests/ -v"
    echo "  pytest tests/py_unit_tests/test_args.py::test_ht_binary_not_available -v"
    echo ""
    
    # Set up Python path to include both environments
    # htty-py-sdist first (priority), then test deps
    export PYTHONPATH="${httyPySdist}/lib/python3.12/site-packages:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"
    
    # Set up PATH (note: deliberately excludes ht binary)
    export PATH="${testDepsEnv}/bin:$PATH"
  '';
} 