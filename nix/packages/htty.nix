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
    htty_core = final.buildPythonPackage {
      pname = "htty-core";
      version = "0.3.0";
      format = "wheel";
      src = httyCoreWheel;
      
      # Create dist directory and copy wheel
      unpackPhase = ''
        mkdir -p dist
        cp ${httyCoreWheel}/*.whl dist/
      '';
      
      # No build needed - it's already a wheel
      dontBuild = true;
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

in
# Create virtual environment with htty and its dependencies (including htty_core)
pythonSet.mkVirtualEnv "htty-env" workspace.deps.default
