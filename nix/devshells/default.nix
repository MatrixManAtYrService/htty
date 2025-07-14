{ pkgs, inputs, system, ... }:

let
  # Get pinned version of vim for use in tests
  lib = inputs.self.lib pkgs;
  inherit (lib.testcfg) testVim;

  # Get overlays for Rust
  overlays = [ inputs.rust-overlay.overlays.default ];
  pkgsWithRust = import inputs.nixpkgs {
    inherit system;
    inherit overlays;
  };

  # Rust toolchain with extensions
  rustToolchain = pkgsWithRust.rust-bin.stable.latest.default.override {
    extensions = [ "rust-src" "clippy" "rustfmt" ];
  };

  # Load the test workspace to get pytest and test dependencies
  testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../tests;
  };

  # Load the htty workspace for editable overlay (Python package only)
  httyWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../htty;
  };

  # Create an overlay enabling editable mode for htty package
  editableOverlay = httyWorkspace.mkEditablePyprojectOverlay {
    # Use environment variable for the root
    root = "$REPO_ROOT";
  };

  # Create python set with test dependencies and editable htty package
  pythonSet = (pkgsWithRust.callPackage inputs.pyproject-nix.build.packages {
    python = pkgsWithRust.python3;
  }).overrideScope (
    pkgsWithRust.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (testWorkspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
      (httyWorkspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
      editableOverlay
      # Custom overrides for editable installs
      (final: prev: {
        # For htty, add editables dependency for hatchling editable builds
        htty = prev.htty.overrideAttrs (old: {
          # Hatchling needs editables package for editable builds (PEP-660)
          nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++
            final.resolveBuildSystem {
              editables = [ ];
            };
        });

        # Provide a minimal stub for htty-core to satisfy uv2nix dependency discovery
        # The actual Python source is provided via PYTHONPATH
        htty-core = pkgsWithRust.python3.pkgs.buildPythonPackage {
          pname = "htty-core";
          version = "0.3.0";
          format = "other";
          src = pkgsWithRust.runCommand "empty-source" { } "mkdir $out";
          dontBuild = true;
          dontInstall = true;
          installPhase = ''
            mkdir -p $out
            echo "Stub package - actual source available via PYTHONPATH" > $out/README
          '';
        };
      })
    ]
  );

  # Combine test dependencies with htty dependencies, excluding htty-core
  httyDepsWithoutCore = builtins.removeAttrs httyWorkspace.deps.default [ "htty-core" ];
  combinedDeps = testWorkspace.deps.default // httyDepsWithoutCore;

  # Create virtual environment with test deps and editable htty (htty_core source available via PYTHONPATH)
  virtualenv = pythonSet.mkVirtualEnv "htty-dev-env" combinedDeps;

in
pkgsWithRust.mkShell {
  buildInputs = with pkgsWithRust; [
    # Virtual environment with editable installs
    virtualenv

    # Rust development
    rustToolchain
    pkg-config
    maturin

    # Python development
    python3
    uv

    # Additional tools
    ruff
    pyright
    nixpkgs-fmt
    nil
    nixd
    nix-output-monitor
    sl
    nodejs

    # Test dependencies
    testVim
  ] ++ pkgsWithRust.lib.optionals pkgsWithRust.stdenv.isDarwin [
    pkgsWithRust.libiconv
  ];

  env = {
    # Don't create venv using uv
    UV_NO_SYNC = "1";

    # Force uv to use Python interpreter from venv
    UV_PYTHON = "${virtualenv}/bin/python";

    # Prevent uv from downloading managed Python's
    UV_PYTHON_DOWNLOADS = "never";
  };

  shellHook = ''
    # Get repository root using git. This is expanded at runtime by the editable .pth machinery.
    export REPO_ROOT=$(git rev-parse --show-toplevel)

    # Set up PYTHONPATH to include htty-core Python source and htty source for editable access
    # htty-core: we can't treat it like the others because it has rust components
    # htty: add source directory for direct editor access to supplement editable install
    export PYTHONPATH="$REPO_ROOT/htty-core/src/python:$REPO_ROOT/htty/src:${virtualenv}/${pkgsWithRust.python3.sitePackages}"

    export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"
    export CARGO_TARGET_DIR="./target"
  '';
}
