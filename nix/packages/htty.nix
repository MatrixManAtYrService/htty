# Complete htty Python environment (htty-core + htty wrapper)
{ inputs, pkgs, perSystem, ... }:

let
  # Get the htty-core wheel to override the dependency
  httyCoreWheel = perSystem.self.htty-core-wheel;

  # Load the htty workspace directly
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../htty;
  };

  # Override htty_core to use our built wheel
  pyprojectOverrides = final: prev: {
    htty-core = pkgs.python3.pkgs.buildPythonPackage {
      pname = "htty-core";
      version = "0.3.0";
      format = "wheel";
      src = httyCoreWheel;

      # Don't build - it's already a wheel
      dontBuild = true;
      dontConfigure = true;

      # Custom unpack for wheel directory
      unpackPhase = ''
        mkdir -p ./dist
        cp ${httyCoreWheel}/*.whl ./dist/
        # Create a simple setup for wheel installation
        sourceRoot="."
      '';

      meta = {
        description = "Headless Terminal - Rust binary with Python bindings";
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
