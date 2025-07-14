# Complete htty Python environment (htty-core + htty wrapper)
{ inputs, pkgs, perSystem, flake, ... }:

let
  # Get version information
  lib = flake.lib pkgs;
  inherit (lib.version) version;

  # Get the htty-core wheel to override the dependency
  httyCoreWheel = perSystem.self.htty-core-wheel;

  # Include only files needed for htty Python package building
  httySource = inputs.nix-filter.lib {
    root = ../../htty;
    include = [
      "src"
      "pyproject.toml"
      "uv.lock"
      "README.md"
      "LICENSE"
    ];
  };

  # Load the htty workspace from filtered source
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = httySource;
  };

  # Override htty_core to use our built wheel
  pyprojectOverrides = final: prev: {
    htty-core = pkgs.python3.pkgs.buildPythonPackage {
      pname = "htty-core";
      inherit version;
      format = "wheel";
      src = httyCoreWheel;

      # Don't build - it's already a wheel
      dontBuild = true;
      dontConfigure = true;

      # Custom unpack for wheel directory
      unpackPhase = ''
        mkdir -p ./dist
        # Copy any .whl files from the wheel directory
        cp ${httyCoreWheel}/*.whl ./dist/ || echo "No wheel files found"
        ls -la ${httyCoreWheel}/
        ls -la ./dist/
        # Create a simple setup for wheel installation
        sourceRoot="."
      '';

      meta = {
        description = "Headless Terminal - Rust binary with Python bindings for htty";
      };
    };
  };

  # Create python set with overrides
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      })
      pyprojectOverrides
    ]
  );

  # Remove htty_core from workspace deps since we provide it via override
  workspaceDeps = builtins.removeAttrs workspace.deps.default [ "htty-core" ];
in
# Create virtual environment with htty and its dependencies (including htty_core)
pythonSet.mkVirtualEnv "htty-env" workspaceDeps
